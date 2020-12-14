from http.server import HTTPServer, BaseHTTPRequestHandler
from torrent_parser import to_torrent
from piece_gen import pieces_gen
import urllib.parse
import bencodepy
import base64
import hashlib
import random

PORT = 9005
TRACKER_ADDR = ("localhost", PORT)
TORRENT_FILE = "./torrents/BACCHUS.torrent"
TRACKER_ID = "BACCHUS ONLY TRACKER"
ALLOWED_PEERS = 30
INTERV_REQ = 30
original_seeder = {
    "peer_id": "FSTSEEDER TORRCLIENT",
    "ip": "localhost",
    "port": "9210",
}
listed_peers = [original_seeder]
tracking_file = ""


def get_infohash():
    # Tambien se consigue el hash del valor del campo info encontrado en archivo torrent
    bencoder = bencodepy.Bencode()
    bdencoded_torrent = bencoder.read(TORRENT_FILE)
    bencoded_info = bencodepy.encode(bdencoded_torrent[b"info"])
    return hashlib.sha1(bencoded_info).digest()


def retrv_peers():
    if len(listed_peers) <= ALLOWED_PEERS + 1:
        return listed_peers
    else:
        shuffled_list = random.shuffle(listed_peers)
        return shuffled_list[: ALLOWED_PEERS + 1]


def do_handshake(curr_peer, info_hash):

    print(get_infohash(), info_hash)
    if get_infohash() == info_hash:
        if curr_peer not in listed_peers:
            listed_peers.append(curr_peer)
        return True
    else:
        return False


def parse_params(url_query):

    params_list = url_query.split("&")
    query_params = {}

    for param in params_list:
        name, value = param.split("=")
        if name == "info_hash":
            query_params[name] = urllib.parse.unquote(value)
        if name == "peer_id":
            query_params[name] = value
        else:
            query_params[name] = value

    return query_params


class trackerHandler(BaseHTTPRequestHandler):
    def query_errors(self, parsed_query):

        # El parametro info_hash tiene escapes '\' de caracteres
        info_hash = base64.b64decode(parsed_query["info_hash"][0])
        # info_hash = parsed_query["info_hash"][0]

        # info_hash = parsed_query["info_hash"][0]
        client_id = parsed_query["peer_id"][0]

        if client_id:
            self.send_response(202, message="Aceptado")
            self.send_header("content-type", "text/plain")
            self.end_headers()
            return False, client_id, info_hash
        elif "info_hash" not in parsed_query:
            self.send_response(101, message="No Funciona")
            self.send_header("content-type", "text/plain")
            self.end_headers()
            return b"Campo info_hash faltante"
        elif "peer_id" not in parsed_query:
            self.send_response(102, message="No Funciona")
            self.send_header("content-type", "text/plain")
            self.end_headers()
            return b"Campo peer_id faltante"
        elif "port" not in parsed_query:
            self.send_response(103, message="No Funciona")
            self.send_header("content-type", "text/plain")
            self.end_headers()
            return b"Campo port faltante"
        elif len(info_hash) != 20:
            self.send_response(150, message="No Funciona")
            self.send_header("content-type", "text/plain")
            self.end_headers()
            return b"info_hash debe ser de 20 bytes"
        elif len(client_id) != 20:
            self.send_response(151, message="No Funciona")
            self.send_header("content-type", "text/plain")
            self.end_headers()
            return b"peer_id debe ser de 20 bytes"
        elif parsed_query["numwant"][0] > ALLOWED_PEERS:
            self.send_response(152, message="Funciona")
            self.send_header("content-type", "text/plain")
            self.end_headers()
            return b"La maxima cantidad de peers permitida es: %s " % ALLOWED_PEERS

    def do_GET(self):

        parsed_url = urllib.parse.urlparse(self.path)
        print(parsed_url)

        parsed_query = urllib.parse.parse_qs(parsed_url.query)

        error, client_id, info_hash = self.query_errors(parsed_query)

        if error:
            self.wfile.write(error)
        else:
            curr_peer = {
                "peer_id": client_id,
                "ip": self.client_address[0],
                "port": parsed_query["port"][0],
            }
            print(curr_peer)
            if do_handshake(curr_peer, info_hash):
                peers_list = [peer for peer in retrv_peers() if peer != curr_peer]
                res = bencodepy.encode(
                    {
                        "interval": INTERV_REQ,
                        "peers": peers_list,
                        "tracker_id": TRACKER_ID,
                    }
                )
                self.wfile.write(res)


if __name__ == "__main__":

    tracker = HTTPServer(TRACKER_ADDR, trackerHandler)
    print("[TRACKER] Tracker escuchando puerto %s" % PORT)
    try:
        tracker.serve_forever()
    except KeyboardInterrupt:
        pass
    tracker.server_close()
    print("[TRACKER] Tracker terminado")
