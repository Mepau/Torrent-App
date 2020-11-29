import select
import socket
import hashlib
import requests
import bencodepy
import pickle
import uuid
import sys

tracker_url = "http://localhost:9005/tracker/announce"
torrent_file = "./torrents/BACCHUS.torrent"
PORT = 9200
peer_addr = ("localhost", PORT)
peer_service = socket.socket(socket.AF_INET, socket.SOCK_STREAM)


def tracker_req(id, hashed_torr, uploaded=None, downloaded=None, numwant=50):
    
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
    )
    
    print(req)


# Funcion principal del thread inicial para llamadas XMLRPC desde y para otros nodos
def run_client(id, hashed_torr):

    tracker_req(id, hashed_torr)

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

    bencoder = bencodepy.Bencode()

    bencoded_torrent = bencoder.read(torrent_file)
    serialized_bencode = pickle.dumps(bencoded_torrent[b"info"])
    hashed_bencode = hashlib.sha1(serialized_bencode).digest()
    client_id = b"".join([uuid.uuid4().bytes, b"0000"])

    peer_service.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    peer_service.setblocking(0)
    peer_service.bind(peer_addr)
    peer_service.listen(5)

    run_client(client_id, hashed_bencode)

    # hashed_info = hashlib.sha1(bencoded_torrent[b"info"])
