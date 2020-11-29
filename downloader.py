import select
import socket
import hashlib
import requests
import bencodepy
import uuid
import base64

tracker_url = "http://localhost:9005/tracker/announce"
torrent_file = "./torrents/BACCHUS.torrent"
PORT = 9200
peer_addr = ("localhost", PORT)
peer_service = socket.socket(socket.AF_INET, socket.SOCK_STREAM)


def tracker_req(id, hashed_torr, uploaded=None, downloaded=None, numwant=50):
    try:
        req = requests.get(
            tracker_url,
            params={
                "info_hash": hashed_torr,
                "peer_id": id,
                "port": PORT,
                "uploaded": uploaded,
                "downloaded": downloaded,
                "numwant": numwant,
            },
            verify=False,
        )
        print(req)
    except requests.exceptions.RequestException as exc:
        print(exc)


# Funcion principal del thread inicial para llamadas XMLRPC desde y para otros nodos
def run_client():

    bencoder = bencodepy.Bencode()

    bdencoded_torrent = bencoder.read(torrent_file)
    bencoded_info = bencodepy.encode(bdencoded_torrent[b"info"])
    hashed_bencode = hashlib.sha1(bencoded_info).digest()
    client_id = "BACCHUS'S TORRCLIENT"

    tracker_req(client_id,  base64.b64encode(hashed_bencode))

    # Socket que se esperan recibir data
    inputs = [peer_service]
    # Lista con socket de los demas nodos
    outputs = []

    print("Starting nodes")

    while inputs:
        # Esperar por la llamada del SO cuando algun socket contenga data
        readable, writable, exceptional = select.select(inputs, outputs, inputs)
        for s in readable:
            if s is peer_service:
                pass
            pass

        for s in writable:
            pass
        # Casos de sockets con excepciones
        for s in exceptional:
            inputs.remove(s)
            if s in outputs:
                outputs.remove(s)
            s.close()


if __name__ == "__main__":

    peer_service.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    peer_service.setblocking(0)
    peer_service.bind(peer_addr)
    peer_service.listen(5)

    run_client()

    # hashed_info = hashlib.sha1(bencoded_torrent[b"info"])
