import select
import socket
import hashlib
import bencodepy
import uuid
import time
from torr_handshake import recv_handshake
from constants import THIS_CLIENT_ID, PORT
from bitarray import bitarray
from peer_actions import PeerActions
from piece_gen import pieces_gen, gen_block, piece_toblocks
from torrent_parser import from_torrent
from file_builder import FileBuilder

PEER_ADDR = ("localhost", PORT)
TORRENT_FILE = "./torrents/BACCHUS.torrent"
# CLIENT_ID = "BACCHUS'S TORRCLIENT"
# CLIENT_ID= "FSTSEEDER TORRCLIENT"
CLIENT_ID = THIS_CLIENT_ID
SEED_FILE = "./seed_file.pdf"
KEEP_ALIVE_TIME = 120.0
TIMEOUT_TIME = 180.0
MAX_UPLOAD_PEER = 4
peer_service = socket.socket(socket.AF_INET, socket.SOCK_STREAM)


def run_client():

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
    upload_peers = 0

    (
        announce_url,
        single_file,
        file_length,
        multi_files,
        pieces_length,
        pieces_amount,
        pieces_hash,
        bencoded_info,
    ) = from_torrent(TORRENT_FILE)

    hashed_info = hashlib.sha1(bencoded_info).digest()

    client_bitfield = bitarray(pieces_amount, endian="big")
    client_bitfield.setall(0)

    if THIS_CLIENT_ID == "FSTSEEDER TORRCLIENT":
        pieces, nhashed_pieces = pieces_gen(SEED_FILE)
        stringed_hashes = b""
        for hash in nhashed_pieces:
            stringed_hashes = b"".join([stringed_hashes, hash])
        print("Comprobando piezas")
        if stringed_hashes == pieces_hash:
            print("MATCH")
            id_count = 0
            for piece in pieces:
                recv_pieces[id_count] = piece_toblocks(piece)
                client_bitfield[id_count] = True
                id_count += 1
        else:
            print("NO MATCH")

    file_builder = FileBuilder(
        client_bitfield,
        single_file,
        file_length,
        multi_files,
        pieces_length,
        pieces_hash,
    )

    peer_actions = PeerActions(inputs, outputs, pstatus_set, conns_ids, file_builder)

    peer_actions.retrv_peers(
        announce_url,
        hashed_info,
        client_bitfield,
    )

    print("Starting nodes")
    keepalive_time = time.time() + KEEP_ALIVE_TIME
    while inputs:
        # Esperar por la llamada del SO cuando algun socket contenga data
        readable, writable, exceptional = select.select(inputs, outputs, inputs)
        for s in readable:
            if s is peer_service:
                conn, addr = s.accept()
                conn.settimeout(3)
                try:
                    peer_id = recv_handshake(hashed_info, conn, client_bitfield)
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
                        peer_actions.handle_req(data, conns_ids[s], request_qs)
                    else:
                        peer_actions.remove_peer(s, request_qs)
                except socket.error as err:
                    print(err)
                    peer_actions.remove_peer(s, request_qs)

        file_builder.check_4pieces()
        curr_time = time.time()
        for s in writable:
            #Esto no deberia de manerjase asi
            try:
                peer_id = conns_ids.get(s)
                peer_bitfield = pstatus_set[peer_id].get("bitfield")
                desired_pindex = peer_bitfield.index(True) if peer_bitfield else None

                if peer_id:
                    if not pstatus_set[peer_id]["am_interested"] and desired_pindex >= 0:
                        s.sendall(b"%b%b" % ((1).to_bytes(4, "big"), (2).to_bytes(1, "big")))
                        print(f"INTERESTED IN {peer_id}")
                        pstatus_set[peer_id]["am_interested"] = True
                    if not pstatus_set[peer_id]["peer_choking"]:
                        pass
                    elif curr_time >= keepalive_time:
                        print(f"Keeping alive {conns_ids[s]}")
                        try:
                            s.sendall((0).to_bytes(4, "big"))
                            keepalive_time = time.time() + KEEP_ALIVE_TIME
                        except socket.error as err:
                            print(err)
            except:
                pass

        # Casos de conexiones con excepciones
        for s in exceptional:
            peer_actions.remove_peer(s, request_qs)

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
