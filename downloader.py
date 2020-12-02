import select
import socket
import hashlib
import requests
import bencodepy
import uuid
import time
import base64
import urllib.parse
from torr_handshake import do_handshake, recv_handshake
from constants import THIS_CLIENT_ID

PORT = 9200
PEER_ADDR = ("localhost", PORT)
TORRENT_FILE = "./torrents/BACCHUS.torrent"
# CLIENT_ID = "BACCHUS'S TORRCLIENT"
# CLIENT_ID= "FSTSEEDER TORRCLIENT"
CLIENT_ID = THIS_CLIENT_ID
KEEP_ALIVE_TIME = 120
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


def retrv_peers(tracker_url, info_hash, inputs, outputs, status_set):

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
                except socket.error as exc:
                    print(exc)


def run_client():

    bencoder = bencodepy.Bencode()

    bdencoded_torrent = bencoder.read(TORRENT_FILE)

    bencoded_info = bencodepy.encode(bdencoded_torrent[b"info"])
    hashed_bencode = hashlib.sha1(bencoded_info).digest()

    pstatus_set = {}

    # Socket que se esperan recibir data
    inputs = [peer_service]
    # Lista con socket de los demas nodos
    outputs = []

    retrv_peers(
        bdencoded_torrent[b"announce"].decode(),
        hashed_bencode,
        inputs,
        outputs,
        pstatus_set,
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
                    peer_id = recv_handshake(hashed_bencode, conn)
                    if peer_id:
                        pstatus_set[peer_id] = {
                            "am_choking": True,
                            "am_interested": False,
                            "peer_choking": True,
                            "peer_interested": False,
                            "last_activity": time.time(),
                            "socket": conn,
                        }

                        conn.setblocking(0)
                        inputs.append(conn)
                        outputs.append(conn)
                    else:
                        conn.close()
                except socket.error as e:
                    print(e)
            else:
                try:
                    data = s.recv(1024)
                    if data:
                        print(data)
                    else:
                        # Para casos en el que los clientes se desconecten
                        if s in outputs:
                            outputs.remove(s)
                        inputs.remove(s)
                        for peer in pstatus_set.items():
                            if peer[1]["socket"] == s:
                                pstatus_set.pop(peer[0])
                                break
                        s.close()
                except socket.error:
                    # Para casos en el que los clientes se desconecten
                    if s in outputs:
                        outputs.remove(s)
                    inputs.remove(s)
                    for peer in pstatus_set.items():
                        if peer[1]["socket"] == s:
                            pstatus_set.pop(peer[0])
                            break
                    s.close()
        for s in writable:
            pass
        # Casos de sockets con excepciones
        for s in exceptional:
            inputs.remove(s)
            if s in outputs:
                outputs.remove(s)
            for peer in pstatus_set.items():
                if peer[1]["socket"] == s:
                    pstatus_set.pop(peer[0])
                    break
            s.close()

        curr_time = time.time()
        for peer in list(pstatus_set.items()):
            print(peer)
            if curr_time >= peer[1]["last_activity"] + float(KEEP_ALIVE_TIME):
                print(f"Timed out{peer[0]}")
                inputs.remove(peer[1]["socket"])
                if peer[1]["socket"] in outputs:
                    outputs.remove(peer[1]["socket"])
                del pstatus_set[peer[0]]
                try:
                    peer[1]["socket"].close()
                except socket.error as err:
                    print(err)
        
        print(pstatus_set)


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
