# Example:  demonstrates TCP/IP TXMODE via HTTP POST of an image

"""
HTTP POST DEMO USING Python TCPIP TX MODE (SIMPLIFIED)
======================================================

This script demonstrates how TCPIP TX MODE can be used to send images
to a server via HTTPS. The demonstration also shows how additional
header information can be generated, in this case the current battery
voltage. The demo requires a FAT32 formatted SD Card to be inserted in 
to the X-Link in order to hold the image. 

This example is simplified version of http_post_file.py that just sends
the image as the payload of the HTTP POST. The downside of this simplified
method is that the file name has to be sent as a custom header field rather
than as part of the post (meaning the HTTP Server will not parse it automatically).

If you are using a version of LinkComm which will not let you set the TXMODE
to Python TCPIP (but are running a version of firmware that supports it) you
will need to click the "Test Script File..." button and the script will set the
necessary fields. If you need to change the setup after that, be sure to
click "Test Script File..." button again.

The demo will transmit any files in the /sd/tx1 folder. If you would 
like to create a fake image to send then run the script task create_image.

The public test server httpbin.org is used to perform the test transmission
and verify the result. The last result can be displayed by running the
script task display_results.

With the following TX1 setup, this script will transmit any images in the
/sd/tx1 folder to httpbin.org test server every hour via secure HTTPS::

!TX1 Enable=On
!TX1 Radio Type=Cell
!TX1 Kind=Scheduled
!TX1 Label=HTTP POST
!TX1 Scheduled Interval=01:00:00
!TX1 Scheduled Time=00:00:00
!TX1 Data Source=File
!TX1 Max Files Per Tx=16
!TX1 File Expiry Period=10080 min
!TX1 Mode=Python TCPIP
!TX1 Secure=On
!TX1 Use Certificate=Off
!TX1 Mode Function=send_image_http
!TX1 Main Server=httpbin.org
!TX1 Backup Server=
!TX1 Server Port=443
!TX1 Server Username=
!TX1 Server Password=
!TX1 Server Path=post

You can attempt the transmission with HTTP rather than secure HTTPS by 
setting the following (not all modems support HTTPS)::

!TX1 Secure=Off
!TX1 Server Port=80

"""

from sl3 import *
from os import stat, urandom

last_results = "No results so far"

def receive_data(socket, amount=1024, iterations=120):
    """
    Receive data from a socket.

    This function calls socket.recv(amount) up to 'iterations' times, 
    concatenating and returning the result. It exits early if after 
    receiving data on one iteration it doesn't receive data on the next.

    :param socket: The socket object to receive data from.
    :type socket: socket.socket
    :param amount: The maximum amount of data to be received at once, defaults to 1024.
    :type amount: int, optional
    :param iterations: The maximum number of iterations to attempt receiving data, defaults to 10.
    :type iterations: int, optional
    :return: The concatenated data received from the socket.
    :rtype: bytes
    """
    result = b''
    data_received = False

    for _ in range(iterations):
        data = socket.recv(amount)
        if data:
            result += data
            data_received = True
        elif data_received:
            break
        else:
            data_received = False

    return result



@TXMODE
def send_image_http(socket, message, file_name):
    """
    Function to send an image file via HTTP POST to httpbin.org.

    :param socket: Open socket for sending/receiving data.
    :param message: Unused (we expect a file transfer)
    :param file_name: Name of the file to be sent ('image.jpg' in this case).
    :return: 0 if HTTP POST was accepted and acknowledged, 1 if there was an issue.
    """
    global last_results

    if is_being_tested():
        print("This function cannot be tested due to file usage and server reply")
        return 1
    
    if file_name is None:
        last_results = "Expected file tranmission"
        print(last_results)
        return 1  # do not retry
        
    CRLF = '\r\n'
    last_results = "Sending file " + file_name
    
    try:
        # Prepare the HTTP POST request headers
        file_size = stat(file_name)[6]
        
        if file_size == 0:
            last_results = "File does not exist or is 0 bytes " & file_name
            print(last_results)
            return 0 # do not retry
        
        headers = [
            'POST /{} HTTP/1.1'.format(path),
            'Host: httpbin.org',
            'Content-Type: image/jpeg',
            'Content-Length: {}'.format(file_size),
            'File-Name: {}'.format(file_name),
            ]

        # Custom header entries can go here (it's easiest to avoid spaces in the field names):
        custom_headers = [
            'Battery-Voltage: {:.2f}'.format(batt()),
            ]

        # Concatenate all headers into a single byte string
        headers_data = CRLF.join(headers) + CRLF + CRLF.join(custom_headers) + 2*CRLF

        last_results = "Sending headers"

        # Send the headers and start of the body
        socket.send(headers_data)

        last_results = "Sending file data"
        
        # Send the file data in 1KB chunks
        with open(file_name, 'rb') as file:
            while True:
                chunk = file.read(1024)  # Read in chunks to conserve memory
                if not chunk:
                    break
                socket.send(chunk)

        # Set a timeout for receiving the HTTP response
        # please note that we are already connected to the server
        # so this is the timeout for server to reply to the POST
        socket.settimeout(3)  # Timeout seconds
        
        last_results = "Receiving reply"

        # Receive the HTTP response, allowing up to 30 seconds
        response = receive_data(socket)
        
        if len(response) == 0:
            response = "<timeout expired>".encode('utf-8')

        last_results = "Server Response:\r\n" + response.decode('utf-8')
        print(last_results)
        
        # Check if the server acknowledged the message
        if b'HTTP/1.1 200 OK' in response or b'HTTP/1.0 200 OK' in response:
            return 0  # HTTP POST accepted and acknowledged
        else:
            return 1  # Server did not acknowledge properly

    except Exception as e:
        last_results = "Transmission failed due to " + str(e)
        print(last_results)
        return 1  # Error occurred, do not retry

@TASK
def create_image():
    """
    Create a fake image to send on the SD card.
    Set the `simple` variable in the function to True if
    you want a small 10 byte image, or to False if you want an image
    consisting of 16KB of random data.
    """
    if not is_being_tested():
        simple = True
        with open("/sd/TX1/test_image.jpg", "wb") as f:
            if simple:
                f.write("1234567890")
            else:
                # create a 16KB test image of random data
                for i in range(16):
                    f.write(urandom(1024))
        print("Test image has been created.")

@TASK
def display_results():
    """
    Display the last results received from the HTTP Server
    """
    global last_results
    print("Last results:")
    print(last_results)


# in case version of LinkComm is being used which can't set these fields, we'll set them for it
if setup_read("tx1 label") == "HTTP POST":
    if setup_read("tx1 mode") != "Python TCPIP":
        setup_write("tx1 mode", "Python TCPIP")
    if setup_read("tx1 mode function") != "send_image_http":
        setup_write("tx1 mode function", "send_image_http")
