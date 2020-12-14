import base64
import urllib.parse
import requests
import socket
import time
import bencodepy
from bitarray import bitarray
from constants import THIS_CLIENT_ID, PORT, MAX_UPLOAD_PEERS
from torr_handshake import do_handshake
from file_builder import FileBuilder


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


class PeerActions:
    def __init__(
        self,
        inputs: list,
        outputs: list,
        pstatus_set: dict,
        conns_ids: dict,
        file_builder: FileBuilder,
        upload_peers: list,
        request_qs: dict,
    ):
        self.inputs = inputs
        self.outputs = outputs
        self.pstatus_set = pstatus_set
        self.file_builder = file_builder
        self.conns_ids = conns_ids
        self.upload_peers = upload_peers
        self.request_qs = request_qs
        

    def change_pstatus(self, len_prefix, msg_id, peer_id):

        if len_prefix == 0:
            self.pstatus_set[peer_id]["last_activity"] = time.time()
        elif len_prefix == 1 and msg_id == 0:
            self.pstatus_set[peer_id]["peer_choking"] = True
            self.pstatus_set[peer_id]["last_activity"] = time.time()
        elif len_prefix == 1 and msg_id == 1:
            self.pstatus_set[peer_id]["peer_choking"] = False
            self.pstatus_set[peer_id]["last_activity"] = time.time()
        elif len_prefix == 1 and msg_id == 2:
            self.pstatus_set[peer_id]["peer_interested"] = True
            self.pstatus_set[peer_id]["last_activity"] = time.time()
            if peer_id not in self.upload_peers:
                if len(self.upload_peers) <= MAX_UPLOAD_PEERS:
                    self.upload_peers.append(peer_id)
                    self.pstatus_set[peer_id].get("socket").sendall(
                        b"%b%b" % ((1).to_bytes(4, "big"), (1).to_bytes(1, "big"))
                    )
                    self.pstatus_set[peer_id]["am_choking"] = False
        elif len_prefix == 1 and msg_id == 3:
            self.pstatus_set[peer_id]["peer_interested"] = False
            self.pstatus_set[peer_id]["last_activity"] = time.time()

    def handle_req(self, data, peer_id: str):

        # Manten conexion viva
        len_prefix = data[0:4]
        msg_id = data[4] if len(data) > 4 else []
        payload = data[5 : len(data)] if len(data) > 5 else []
        len_prefix = int.from_bytes(len_prefix, "big")
        peer_socket = self.pstatus_set[peer_id]["socket"]

        # Mensaje recibido de peer por cambio de estado
        if len_prefix <= 1:
            self.change_pstatus(len_prefix, msg_id, peer_id)
        # Recepcion de Bitfield correspondiente a las piezas recibido del peer
        elif msg_id == 5 and len_prefix == len(payload) + 1:
            barray = bitarray(endian="big")
            barray.frombytes(payload)
            self.pstatus_set[peer_id]["bitfield"] = barray
            self.pstatus_set[peer_id]["last_activity"] = time.time()
            print(f"Bitfield {barray} de Peer {peer_id}")
        # Recepcion de mensaje de peer solicitando un bloque para pieza
        elif msg_id == 6 and len_prefix == 13:
            piece_index = int.from_bytes(payload[0:4], "big")
            block_start = int.from_bytes(payload[4:8], "big")
            block_length = int.from_bytes(payload[8:12], "big")
            # Cada request es insertado en una cola por cada peer
            self.request_qs[peer_socket].append(
                (piece_index, block_start, block_length)
            )
            self.pstatus_set[peer_id]["last_activity"] = time.time()
            print(f"Request recibido de Peer {peer_id}")
        # Recepcion de bloque solicitado a peer
        elif msg_id == 7 and len_prefix > 9:

            block = payload[8 : len(payload)]
            piece_index = int.from_bytes(payload[0:4], "big")
            block_start = int.from_bytes(payload[4:8], "big")

            self.file_builder.insert_block(piece_index, block_start, block)
            self.pstatus_set[peer_id]["last_activity"] = time.time()
            # Cada request es insertado en una cola por cada
            print(f"Bloque recibido de Peer {peer_id}")
        # Cancelar peticion de bloque
        elif msg_id == 8 and len_prefix == 13 and len(payload) == len_prefix:
            piece_index = int.from_bytes(payload[0:4], "big")
            block_start = int.from_bytes(payload[5:9], "big")
            block_length = int.from_bytes(payload[9:13], "big")
            # Cada request es insertado en una cola por cada peer
            if self.pstatus_set[peer_id]["socket"] in self.request_qs:
                if (piece_index, block_start, block_length) in self.request_qs[
                    peer_socket
                ]:
                    self.request_qs[peer_socket].remove(
                        (piece_index, block_start, block_length)
                    )
                    print(f"Peticion cancelada de Peer {peer_id}")
            self.pstatus_set[peer_id]["last_activity"] = time.time()

    def retrv_peers(self, tracker_url, info_hash, client_bitfield):

        encoded_hash = base64.b64encode(info_hash)
        peers_list = tracker_req(tracker_url, encoded_hash)

        if peers_list:
            print(f"Peers list {peers_list}")
            for peer in peers_list:
                peer_id = peer[b"peer_id"].decode()
                if peer_id not in self.pstatus_set and peer_id != THIS_CLIENT_ID:
                    new_peer = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    new_peer.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                    peer_address = (peer[b"ip"].decode(), int(peer[b"port"].decode()))
                    try:
                        new_peer.connect(peer_address)
                        if do_handshake(
                            info_hash, new_peer, peer[b"peer_id"], client_bitfield
                        ):
                            self.inputs.append(new_peer)
                            self.outputs.append(new_peer)
                            self.pstatus_set[peer_id] = {
                                "am_choking": True,
                                "am_interested": False,
                                "peer_choking": True,
                                "peer_interested": False,
                                "last_activity": time.time(),
                                "socket": new_peer,
                            }
                            self.conns_ids[new_peer] = peer_id
                            self.request_qs[new_peer] = []

                            new_peer.setblocking(0)
                        else:
                            new_peer.close()
                    except socket.error as exc:
                        print(exc)

    def remove_peer(
        self,
        sokt,
    ):
        self.inputs.remove(sokt)
        if sokt in self.outputs:
            self.outputs.remove(sokt)
        if self.conns_ids[sokt] in self.pstatus_set:
            self.pstatus_set.pop(self.conns_ids[sokt])
        if self.conns_ids[sokt] in self.upload_peers:
            self.upload_peers.remove(self.conns_ids[sokt])
        if sokt in self.conns_ids:
            self.conns_ids.pop(sokt)
        if sokt in self.request_qs:
            del self.request_qs[sokt]
        sokt.close()
