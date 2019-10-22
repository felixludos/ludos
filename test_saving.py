import json
from flask import Flask, request

app = Flask(__name__)

@app.route('/post', methods=['POST'])
def post_route():
	if request.method == 'POST':

		# data = request.get_json(force=True)
		data = json.loads(request.data)
		
		print(request.data)

		print('Data Received: {data}'.format(data=data))
		return "Request Processed.\n"

app.run(debug=True)
