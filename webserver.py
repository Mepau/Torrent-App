from http.server import HTTPServer, BaseHTTPRequestHandler
from torrent_parser import to_torrent
from piece_gen import pieces_gen, DEF_PIECE_LENGTH

PORT = 9000
SERVER_ADDR = ("localhost", PORT)

TRACKER_URL = "http://localhost:9005/tracker/announce"
tracked_file = "./peer_files"
TORRENT_FNAME = "BACCHUS.torrent"


class requestHandler(BaseHTTPRequestHandler):
    def do_GET(self):

        if self.path.endswith(f"/path_to/{TORRENT_FNAME}"):
            self.send_response(200)
            self.send_header("content-type", "application/x-bittorrent")
            self.end_headers()

            _, pieces_hash = pieces_gen(tracked_file)

            stringed_hashes = b""
            for hash in pieces_hash:
                stringed_hashes = b"".join([stringed_hashes, hash])

            output = to_torrent(
                tracked_file, TRACKER_URL, stringed_hashes, DEF_PIECE_LENGTH
            )

            with open(f"./torrents/{TORRENT_FNAME}", "wb") as torrent:
                torrent.write(output)

            self.wfile.write(output)


if __name__ == "__main__":

    server = HTTPServer(SERVER_ADDR, requestHandler)
    print("[SERVIDOR] Servidor escuchando puerto %s" % PORT)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    print("[SERVIDOR] Servidor terminado")
