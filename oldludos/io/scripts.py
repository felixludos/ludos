
import sys, os

import omnifig as fig



@fig.Script('start-server', description='Start a ludos server')
def start_server(A):
	
	server = A.pull('server')
	
	address = server.get_address()
	
	if address is not None:
		A.push('address', address)
	
	server.run()
	
	return server


@fig.Script('get-client', description='Create a ludos client')
def create_client(A):
	
	return A.pull('client')

	

