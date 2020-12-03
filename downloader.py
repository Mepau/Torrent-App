import select
import socket
import hashlib
import bencodepy
import uuid
import time
from torr_handshake import recv_handshake
from constants import THIS_CLIENT_ID, PORT
from bitarray import bitarray
from peer_actions import retrv_peers, remove_peer, handle_req

PEER_ADDR = ("localhost", PORT)
TORRENT_FILE = "./torrents/BACCHUS.torrent"
# CLIENT_ID = "BACCHUS'S TORRCLIENT"
# CLIENT_ID= "FSTSEEDER TORRCLIENT"
CLIENT_ID = THIS_CLIENT_ID
KEEP_ALIVE_TIME = 120.0
TIMEOUT_TIME = 140.0
peer_service = socket.socket(socket.AF_INET, socket.SOCK_STREAM)


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
    recv_pieces = {}
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
                        request_qs[conn] = []
                    else:
                        conn.close()
                except socket.error as e:
                    print(e)
            else:
                try:
                    data = s.recv(16384)
                    if data:
                        print(f"Mensaje recibido de {conns_ids[s]}: {data}")

                        handle_req(
                            data,
                            conns_ids[s],
                            request_qs,
                            pstatus_set,
                            recv_pieces,
                        )

                    else:
                        remove_peer(
                            s, inputs, outputs, pstatus_set, conns_ids, request_qs
                        )
                except socket.error as err:
                    print(err)
                    remove_peer(s, inputs, outputs, pstatus_set, conns_ids, request_qs)

        curr_time = time.time()
        for s in writable:
            if curr_time >= keepalive_time:
                print(f"Keeping alive {conns_ids[s]}")
                s.sendall((0).to_bytes(4, "big"))
                keepalive_time = time.time() + KEEP_ALIVE_TIME

        # Casos de sockets con excepciones
        for s in exceptional:
            remove_peer(s, inputs, outputs, pstatus_set, conns_ids, request_qs)

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
