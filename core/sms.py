
import time
from sinchsms import SinchSMS
number = '+353xxxxxxxxx'

import sys, getopt


print sys.argv[1]
message = sys.argv[1]

client = SinchSMS( Insert your Sinch API KEY here )

print("Sending '%s' to %s" % (message, number))
response = client.send_message(number, message)
message_id = response['messageId']
response = client.check_status(message_id)
while response['status'] != 'Successful':
	print(response['status'])
	time.sleep(1)
	response = client.check_status(message_id)
print(response['status'])

