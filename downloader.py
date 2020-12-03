import select
import socket
import hashlib
import requests
import bencodepy
import uuid
import time
import base64
import urllib.parse
import queue
from torr_handshake import do_handshake, recv_handshake
from constants import THIS_CLIENT_ID
from bitarray import bitarray

PORT = 9200
PEER_ADDR = ("localhost", PORT)
TORRENT_FILE = "./torrents/BACCHUS.torrent"
# CLIENT_ID = "BACCHUS'S TORRCLIENT"
# CLIENT_ID= "FSTSEEDER TORRCLIENT"
CLIENT_ID = THIS_CLIENT_ID
KEEP_ALIVE_TIME = 120.0
TIMEOUT_TIME = 140.0
peer_service = socket.socket(socket.AF_INET, socket.SOCK_STREAM)


def tracker_req(tracker_url, hashed_torr, uploaded=None, downloaded=None, numwant=50):
    try:
        payload = urllib.parse.urlencode(
            {
                "info_hash": hashed_torr,
                "peer_id": CLIENT_ID,
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


def retrv_peers(tracker_url, info_hash, inputs, outputs, status_set, conns_ids):

    encoded_hash = base64.b64encode(info_hash)
    peers_list = tracker_req(tracker_url, encoded_hash)

    if peers_list:
        for peer in peers_list:
            if peer[b"peer_id"].decode() not in status_set:
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


def handle_pstatus(len_prefix, msg_id, peer_id, pstatus_set):

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


def remove_peer(sokt, inputs, outputs, pstatus_set, conns_ids):
    if sokt in outputs:
        outputs.remove(sokt)
    inputs.remove(sokt)
    if conns_ids[sokt] in pstatus_set:
        pstatus_set.pop(conns_ids[sokt])
        conns_ids.pop(sokt)
    sokt.close()


def run_client():

    bencoder = bencodepy.Bencode()

    bdencoded_torrent = bencoder.read(TORRENT_FILE)
    pieces_hash = bdencoded_torrent[b"info"][b"pieces"]
    pieces_amount = len(pieces_hash) // 20
    bencoded_info = bencodepy.encode(bdencoded_torrent[b"info"])
    hashed_info = hashlib.sha1(bencoded_info).digest()

    keepalive_time = time.time() + KEEP_ALIVE_TIME

    # Diccionario lista con el estado de cada conexion/peer
    pstatus_set = {}
    # Diccionario para rapida referencia entre conexion y peer_id
    conns_ids = {}

    # Socket que se esperan recibir data
    inputs = [peer_service]
    # Lista con socket de los demas nodos
    outputs = []

    request_qs = {}

    retrv_peers(
        bdencoded_torrent[b"announce"].decode(),
        hashed_info,
        inputs,
        outputs,
        pstatus_set,
        conns_ids,
    )

    print("Starting nodes")

    while inputs:
        # Esperar por la llamada del SO cuando algun socket contenga data
        readable, writable, exceptional = select.select(inputs, outputs, inputs)
        for s in readable:
            if s is peer_service:
                conn, addr = s.accept()
                conn.settimeout(3)
                try:
                    peer_id = recv_handshake(hashed_info, conn)
                    if peer_id:
                        pstatus_set[peer_id] = {
                            "am_choking": True,
                            "am_interested": False,
                            "peer_choking": True,
                            "peer_interested": False,
                            "last_activity": time.time(),
                            "socket": conn,
                            "bitfield": None,
                        }
                        conns_ids[conn] = peer_id

                        conn.setblocking(0)
                        inputs.append(conn)
                        outputs.append(conn)
                        request_qs[conn] = queue.Queue()
                    else:
                        conn.close()
                except socket.error as e:
                    print(e)
            else:
                try:
                    data = s.recv(16384)
                    if data:
                        print(f"Mensaje recibido de {conns_ids[s]}: {data}")
                        # Manten conexion viva
                        len_prefix = int.from_bytes(data[0:4], "big")
                        msg_id = (
                            int.from_bytes(data[5], "big") if len(data) == 5 else -1
                        )
                        payload = (
                            int.from_bytes(data[6 : len(data)], "big")
                            if len(data) > 6
                            else -1
                        )
                        # Mensaje recibido de peer por cambio de estado
                        if len_prefix <= 1:
                            handle_pstatus(
                                len_prefix,
                                msg_id,
                                pstatus_set[conns_ids[s]],
                                pstatus_set,
                            )
                        # Recepcion de Bitfield correspondiente a las piezas recibido del peer
                        elif msg_id == 5 and len_prefix == len(payload) + 1:
                            barray = bitarray(endian="big")
                            barray.frombytes(payload)
                            pstatus_set[conns_ids[s]]["bitfield"] = barray
                            print(
                                f"Bitfield {barray} de Peer {pstatus_set[conns_ids[s]]}"
                            )
                        # Recepcion de mensaje de peer solicitando un bloque para pieza
                        elif msg_id == 6 and len(payload) == 13:
                            piece_index = int.from_bytes(payload[0:4], endian="big")
                            block_start = int.from_bytes(payload[5:9], endian="big")
                            block_length = int.from_bytes(payload[9:13], endian="big")
                            # Cada request es insertado en una cola por cada peer
                            request_qs[s].put((piece_index, block_start, block_length))
                            print(
                                f"Request recibido de Peer {pstatus_set[conns_ids[s]]}"
                            )
                        # Recepcion de bloque solicitado a peer
                        elif msg_id == 7 and len_prefix == len(payload) + 9:
                            piece_index = int.from_bytes(payload[0:4], endian="big")
                            block_start = int.from_bytes(payload[5:9], endian="big")
                            block_length = int.from_bytes(payload[9:13], endian="big")
                            # Cada request es insertado en una cola por cada peer
                            request_qs[s].put((piece_index, block_start, block_length))
                            print(
                                f"Request recibido de Peer {pstatus_set[conns_ids[s]]}"
                            )

                    else:
                        remove_peer(s, inputs, outputs, pstatus_set, conns_ids)
                except socket.error:
                    remove_peer(s, inputs, outputs, pstatus_set, conns_ids)

        curr_time = time.time()
        for s in writable:
            if curr_time >= keepalive_time:
                print(f"Keeping alive {conns_ids[s]}")
                s.sendall((0).to_bytes(4, "big"))
                keepalive_time = time.time() + KEEP_ALIVE_TIME

        # Casos de sockets con excepciones
        for s in exceptional:
            remove_peer(s, inputs, outputs, pstatus_set, conns_ids)

        curr_time = time.time()
        for peer in list(pstatus_set.items()):
            if curr_time >= peer[1]["last_activity"] + TIMEOUT_TIME:
                print(f"Timed out{peer[0]}")
                inputs.remove(peer[1]["socket"])
                if peer[1]["socket"] in outputs:
                    outputs.remove(peer[1]["socket"])
                del pstatus_set[peer[0]]
                conns_ids.pop(peer[1]["socket"])
                try:
                    peer[1]["socket"].close()
                except socket.error as err:
                    print(err)


if __name__ == "__main__":

    peer_service.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    peer_service.setblocking(0)
    peer_service.bind(PEER_ADDR)
    peer_service.listen(5)

    try:
        run_client()
    except KeyboardInterrupt:
        print("[DOWNLOADER] Downloader terminado")
    # hashed_info = hashlib.sha1(bencoded_torrent[b"info"])
