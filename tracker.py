from http.server import HTTPServer, BaseHTTPRequestHandler
from torrent_parser import to_torrent
from piece_gen import pieces_gen
from urllib.parse import urlparse

tracking_file = ""
torrent_file = "./torrents/BACCHUS.torrent"

class trackerHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        
        parsed_url = urlparse(self.path)

        print(parsed_url)
        self.send_response(200)
        self.send_header("content-type", "")
        self.end_headers()
        


def run_tracker():

    PORT = 9200
    tracker_addr = ("localhost", PORT)
    tracker = HTTPServer(tracker_addr, trackerHandler)
    print("[TRACKER] Tracker escuchando puerto %s" % PORT)
    tracker.serve_forever()


if __name__ == "__main__":
    run_tracker()
