import base64
import urllib.parse
import requests
import socket
import time
import bencodepy
from bitarray import bitarray
from constants import THIS_CLIENT_ID, PORT
from torr_handshake import do_handshake


def tracker_req(tracker_url, hashed_torr, uploaded=None, downloaded=None, numwant=50):
    try:
        payload = urllib.parse.urlencode(
            {
                "info_hash": hashed_torr,
                "peer_id": THIS_CLIENT_ID,
                "port": PORT,
                "uploaded": uploaded,
                "downloaded": downloaded,
                "numwant": numwant,
                "left": None,
            }
        )
        req = requests.get(tracker_url, params=payload, verify=False)
        res = bencodepy.decode(req.content)[b"peers"]
        return res
    except requests.exceptions.RequestException as exc:
        print(exc)


def handle_req(data, peer_id, req_queue, pstatus_set, pieces_list):

    # Manten conexion viva
    len_prefix = int.from_bytes(data[0:4], "big")
    msg_id = int.from_bytes(data[5], "big") if len(data) == 5 else -1
    payload = int.from_bytes(data[6 : len(data)], "big") if len(data) > 6 else -1
    # Mensaje recibido de peer por cambio de estado
    if len_prefix <= 1:
        change_pstatus(
            len_prefix,
            msg_id,
            peer_id,
            pstatus_set,
        )
    # Recepcion de Bitfield correspondiente a las piezas recibido del peer
    elif msg_id == 5 and len_prefix == len(payload) + 1:
        barray = bitarray(endian="big")
        barray.frombytes(payload)
        pstatus_set[peer_id]["bitfield"] = barray
        print(f"Bitfield {barray} de Peer {peer_id}")
    # Recepcion de mensaje de peer solicitando un bloque para pieza
    elif msg_id == 6 and len(payload) == 13:
        piece_index = int.from_bytes(payload[0:4], endian="big")
        block_start = int.from_bytes(payload[5:9], endian="big")
        block_length = int.from_bytes(payload[9:13], endian="big")
        # Cada request es insertado en una cola por cada peer
        req_queue[pstatus_set[peer_id]["socket"]].append((piece_index, block_start, block_length))
        print(f"Request recibido de Peer {peer_id}")
    # Recepcion de bloque solicitado a peer
    elif msg_id == 7 and len(payload) > 9:
        piece_index = int.from_bytes(payload[0:4], endian="big")
        block_start = int.from_bytes(payload[5:9], endian="big")
        block = payload[9 : len(payload)]
        block_length = len(block)
        pieces_list[piece_index].append(
            {
                "block_start": block_start,
                "block_length": block_length,
                "block": block,
            }
        )
        # Cada request es insertado en una cola por cada
        print(f"Bloque recibido de Peer {peer_id}")
    # Cancelar peticion de bloque
    elif msg_id == 8 and len(payload) == 13:
        piece_index = int.from_bytes(payload[0:4], endian="big")
        block_start = int.from_bytes(payload[5:9], endian="big")
        block_length = int.from_bytes(payload[9:13], endian="big")
        # Cada request es insertado en una cola por cada peer
        if (piece_index, block_start, block_length) in req_queue:
            req_queue[pstatus_set[peer_id]["socket"]].remove((piece_index, block_start, block_length))
            print(f"Peticion cancelada de Peer {peer_id}")


def retrv_peers(tracker_url, info_hash, inputs, outputs, status_set, conns_ids):

    encoded_hash = base64.b64encode(info_hash)
    peers_list = tracker_req(tracker_url, encoded_hash)

    if peers_list:
        print(f"Peers list {peers_list}")
        for peer in peers_list:
            if (
                peer[b"peer_id"].decode() not in status_set
                and peer[b"peer_id"].decode() != THIS_CLIENT_ID
            ):
                new_peer = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                new_peer.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                # new_peer.setblocking(0)
                peer_address = (peer[b"ip"].decode(), int(peer[b"port"].decode()))
                try:
                    new_peer.connect(peer_address)
                    if do_handshake(info_hash, new_peer, peer[b"peer_id"]):
                        inputs.append(new_peer)
                        outputs.append(new_peer)
                        status_set[peer[b"peer_id"].decode()] = {
                            "am_choking": True,
                            "am_interested": False,
                            "peer_choking": True,
                            "peer_interested": False,
                            "last_activity": time.time(),
                            "socket": new_peer,
                        }
                        conns_ids[new_peer] = peer[b"peer_id"].decode()
                        new_peer.setblocking(0)
                    else:
                        new_peer.close()
                except socket.error as exc:
                    print(exc)


def change_pstatus(len_prefix, msg_id, peer_id, pstatus_set):

    if len_prefix == 0:
        pstatus_set[peer_id]["last_activity"] = time.time()
    elif len_prefix == 1 and msg_id == 0:
        pstatus_set[peer_id]["peer_choking"] = True
    elif len_prefix == 1 and msg_id == 1:
        pstatus_set[peer_id]["peer_choking"] = False
    elif len_prefix == 1 and msg_id == 2:
        pstatus_set[peer_id]["peer_interested"] = True
    elif len_prefix == 1 and msg_id == 3:
        pstatus_set[peer_id]["peer_interested"] = False


def remove_peer(sokt, inputs, outputs, pstatus_set, conns_ids, request_qs):
    inputs.remove(sokt)
    if sokt in outputs:
        outputs.remove(sokt)
    if conns_ids[sokt] in pstatus_set:
        pstatus_set.pop(conns_ids[sokt])
    if sokt in conns_ids:
        conns_ids.pop(sokt)
    if sokt in request_qs:
        del request_qs[sokt]
    sokt.close()
