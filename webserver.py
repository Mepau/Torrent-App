from http.server import HTTPServer, BaseHTTPRequestHandler
from torrent_parser import to_torrent
from piece_gen import pieces_gen

tracker_url = "http://localhost:9200/tracker/announce"
tracked_file = "./peer_files"
torrent_fname = "BACCHUS.torrent"


class requestHandler(BaseHTTPRequestHandler):
    def do_GET(self):

        if self.path.endswith(f"/path_to/{torrent_fname}"):
            self.send_response(200)
            self.send_header("content-type", "application/x-bittorrent")
            self.end_headers()

            _, pieces_hash = pieces_gen(tracked_file)

            stringed_hashes = b""
            for hash in pieces_hash:
                stringed_hashes = b"".join([stringed_hashes, hash])

            output = to_torrent(tracked_file, tracker_url, stringed_hashes)

            with open(f"./torrents/{torrent_fname}", "wb") as torrent:
                torrent.write(output)

            self.wfile.write(output)


def run_server():

    PORT = 9000
    server_addr = ("localhost", PORT)

    server = HTTPServer(server_addr, requestHandler)
    print("[SERVIDOR] Servidor escuchando puerto %s" % PORT)
    server.serve_forever()


if __name__ == "__main__":
    run_server()
