import sys, os
import json
import time
from flask import Flask, request

app = Flask(__name__)

@app.route('/post', methods=['POST'])
def post_route():
	if request.method == 'POST':

		try:
			data = request.get_json(force=True)
		except:
			data = json.loads(request.data)

		print(request.data)

		print('Data Received: {data}'.format(data=data))
		return "Request Processed.\n"


# def worker_run()




from subprocess import Popen, PIPE

# def run(command):
# 	process = Popen(command, stdout=PIPE, shell=True)
# 	while True:
# 		line = process.stdout.readline().rstrip()
# 		if not line:
# 			break
# 		yield line


if __name__ == "__main__":
	app.run(debug=True)
# 	# for path in run("ping -c 5 google.com"):
# 	#     print(path.decode())
# 	print('starting')
# 	for i in range(10):
# 		print('msg: {}'.format(i))
# 		time.sleep(1)
# 	print('completed')
# 	sys.exit(2)

