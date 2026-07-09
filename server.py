import socket
import threading
import os
import mimetypes

HOST = "127.0.0.1"
PORT = 9090
STATIC_DIR = "static"

ALLOWED_FOLDERS = {"", "css", "docs", "files", "images"}


def read_http_request(client_socket):
    data = b""

    while b"\r\n\r\n" not in data:
        chunk = client_socket.recv(1024)

        if not chunk:
            break

        data += chunk

        if len(data) > 8192:
            return None

    return data


def parse_request(request_data):
    try:
        request_text = request_data.decode("ascii")
        request_line = request_text.split("\r\n")[0]
        parts = request_line.split()

        if len(parts) != 3:
            return None

        method, path, version = parts
        return method, path, version

    except Exception:
        return None


def create_error_response(status_code, reason):
    body = f"<html><body><h1>{status_code} {reason}</h1></body></html>"
    body_bytes = body.encode("utf-8")

    response = (
        f"HTTP/1.0 {status_code} {reason}\r\n"
        "Content-Type: text/html; charset=utf-8\r\n"
        f"Content-Length: {len(body_bytes)}\r\n"
        "Connection: close\r\n"
        "\r\n"
    ).encode("ascii") + body_bytes

    return response


def get_content_type(file_path):
    content_type, _ = mimetypes.guess_type(file_path)

    if content_type is None:
        return "application/octet-stream"

    return content_type


def is_path_allowed(path):
    if ".." in path:
        return False

    clean_path = path.lstrip("/")

    if clean_path == "":
        return True

    first_folder = clean_path.split("/")[0]

    if "/" in clean_path and first_folder not in ALLOWED_FOLDERS:
        return False

    return True


def build_file_path(path):
    if path == "/":
        path = "/index.html"

    clean_path = path.lstrip("/")
    return os.path.join(STATIC_DIR, clean_path)


def handle_client(client_socket):
    try:
        request = read_http_request(client_socket)

        if request is None:
            client_socket.sendall(create_error_response(400, "Bad Request"))
            return

        parsed = parse_request(request)

        if parsed is None:
            client_socket.sendall(create_error_response(400, "Bad Request"))
            return

        method, path, version = parsed

        if method != "GET":
            client_socket.sendall(create_error_response(400, "Bad Request"))
            return

        if version not in ["HTTP/1.0", "HTTP/1.1"]:
            client_socket.sendall(create_error_response(400, "Bad Request"))
            return

        if not is_path_allowed(path):
            client_socket.sendall(create_error_response(400, "Bad Request"))
            return

        file_path = build_file_path(path)

        if not os.path.isfile(file_path):
            client_socket.sendall(create_error_response(404, "Not Found"))
            return

        with open(file_path, "rb") as file:
            body = file.read()

        response_headers = (
            "HTTP/1.0 200 OK\r\n"
            f"Content-Type: {get_content_type(file_path)}\r\n"
            f"Content-Length: {len(body)}\r\n"
            "Connection: close\r\n"
            "\r\n"
        ).encode("ascii")

        client_socket.sendall(response_headers + body)

    except Exception as error:
        print("Server error:", error)
        try:
            client_socket.sendall(create_error_response(500, "Internal Server Error"))
        except Exception:
            pass

    finally:
        client_socket.close()


def start_server():
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    server_socket.bind((HOST, PORT))
    server_socket.listen(10)

    print(f"Server is running on http://{HOST}:{PORT}")

    while True:
        client_socket, client_address = server_socket.accept()
        print(f"New connection from {client_address}")

        thread = threading.Thread(
            target=handle_client,
            args=(client_socket,)
        )
        thread.start()


if __name__ == "__main__":
    start_server()