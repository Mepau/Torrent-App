from http.server import HTTPServer, BaseHTTPRequestHandler
from torrent_parser import to_torrent
from piece_gen import pieces_gen
from urllib.parse import urlparse, parse_qs
import bencodepy
import base64
import hashlib

PORT = 9005
tracker_addr = ("localhost", PORT)
tracking_file = ""
torrent_file = "./torrents/BACCHUS.torrent"
allowed_peers = 50


class trackerHandler(BaseHTTPRequestHandler):
    def get_infohash(self):

        try:
            return self.hashed_info
        except AttributeError:
            bencoder = bencodepy.Bencode()
            bdencoded_torrent = bencoder.read(torrent_file)
            bencoded_info = bencodepy.encode(bdencoded_torrent[b"info"])
            self.hashed_info = hashlib.sha1(bencoded_info).digest()
            print(self.hashed_info)
            return self.hashed_info

    def do_handshake(self, query):

        # El parametro info_hash tiene escapes '\' de caracteres
        info_hash = base64.b64decode(query["info_hash"][0])
        if self.get_infohash() == info_hash:
            return query["peer_id"][0], info_hash
        else:
            return False, None

    def do_GET(self):

        parsed_url = urlparse(self.path)
        parsed_query = parse_qs(parsed_url.query)
        client_id, info_hash = self.do_handshake(parsed_query)
        print(parsed_query)

        if client_id:
            self.send_response(202, message="Funciona")
            self.end_headers()
        elif "info_hash" not in parsed_query:
            print("No info Hash")
        elif "peer_id" not in parsed_query:
            print("No peer id")
        elif "port" not in parsed_query:
            print("No port")
        elif len(info_hash) != 20:
            print("Info hash not 20 bytes long")
        elif len(client_id) != 20:
            print("Peer id not 20 bytes long")
        elif parsed_query["numwant"][0] > allowed_peers:
            print(f"La maxima cantidad de peers permitida es: {allowed_peers} ")


if __name__ == "__main__":

    tracker = HTTPServer(tracker_addr, trackerHandler)
    print("[TRACKER] Tracker escuchando puerto %s" % PORT)
    try:
        tracker.serve_forever()
    except KeyboardInterrupt:
        pass
    tracker.server_close()
    print("[TRACKER] Tracker terminado")
