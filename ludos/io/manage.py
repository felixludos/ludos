
import sys, os
import traceback

from ..errors import WrappedException


def wrap_exception(cmd, *args, **kwargs):
	try:
		return cmd(*args, **kwargs)
	except Exception as e:
		if isinstance(e, WrappedException):
			msg = {'error' :{'type': str(e.etype), 'msg': e.emsg}}
		else:
			
			msg = {
				'error': {
					'type': e.__class__.__name__,
					'msg': ''.join(traceback.format_exception(*sys.exc_info())),
				},
			}
		return msg




