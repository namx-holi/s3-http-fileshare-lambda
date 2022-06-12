import base64
import boto3
import json
import os.path


s3 = boto3.client("s3")
BUCKET_NAME = os.environ.get("S3_BUCKET_NAME")
REGION_NAME = os.environ.get("S3_REGION_NAME")

prefix_dir = "public"


def _bytes_to_readable(num, suffix=""):
	for unit in ["", "K", "M", "G", "T", "P", "E", "Z"]:
		if abs(num) < 1000.0:
			return f"{num:3.1f}{unit}{suffix}"
		num /= 1000.0
	return f"{num:.1f}Y{suffix}"


class Item:
	def __init__(self, is_dir, path, last_modified="", size=0, description=""):
		self.is_dir = is_dir

		if self.is_dir:
			# Strip the prefix dir out of the path
			self.path = path[len(prefix_dir):]

			# Dir ends in / which messes with basename
			self.name = os.path.basename(self.path.rstrip("/"))

		else:
			# Direct path to S3 file
			self.path = f"https://{BUCKET_NAME}.s3.{REGION_NAME}.amazonaws.com/{path}"

			# Strip the prefix dir out of the path to use for name
			self.name = os.path.basename(path[len(prefix_dir):])

		self.last_modified = last_modified
		self.size = size # In bytes
		self.description = description



class PathHandler:

	@classmethod
	def __call__(cls, event):
		# Get the requested path
		query_string_params = event.get("queryStringParameters", {})
		path = query_string_params.get("path", "").lstrip("/")

		# Sorting by something
		if "?C=" in path:
			# Reverse the path first then split so we definitely get the last ?
			path, sort_string = path.rsplit("?", -1)
		else:
			sort_string = "C=N;O=A" # By default, sort by name ascending


		# If the path ends in a /, or is empty (root dir), we'll assume it's a directory
		if path.endswith("/") or path == "":
			query = s3.list_objects(Bucket=BUCKET_NAME, Prefix=prefix_dir+"/"+path, Delimiter="/")
			
			items = []

			# Subdirectories of the given path
			subdirs = [d for d in query.get("CommonPrefixes",[])]
			for subdir in subdirs:
				items.append(Item(
					is_dir=True,
					path=subdir["Prefix"]
				))

			# Standalone keys in the given path
			objects = [o for o in query.get("Contents",[]) if o["Size"] != 0]
			for obj in objects:
				items.append(Item(
					is_dir=False,
					path=obj["Key"],
					last_modified=obj["LastModified"],
					size=obj["Size"]
				))


			view = cls.construct_directory_view(path, items, sort_string)
			return {
				"headers": {"Content-Type": "text/html"},
				"statusCode": 200,
				"body": view
			}

		# Otherwise, tried to open a file. Return a 404 as we actually redirect to S3
		else:
			return {
				"headers": {"Content-Type": "text/html"},
				"statusCode": 404,
				"body": f"{path} not found. Try clicking on the link :)"
			}

			# audio = response["Body"].read()
			# return {
			# 	"headers": {"Content-Type": "audio/mpeg"},
			# 	"statusCode": 200,
			# 	"body": base64.b64encode(audio).decode("utf-8"),
			# 	"isBase64Encoded": True
			# }


	@classmethod
	def _sort_items(self, items, order_by, reversed_order):
		dirs = [i for i in items if i.is_dir]
		files = [i for i in items if not i.is_dir]
		items = []

		# Always put directories first
		items += sorted(dirs, )




	@classmethod
	def construct_directory_view(cls, path, items, sort_string):
		parent_dir_path = "/" + os.path.dirname(path.rstrip("/"))
		if parent_dir_path != "/":
			# Add a / on the end so that it's recognised as a dir
			parent_dir_path += "/"

		# Sort out ordering of files pun intended :)
		sort_by, order = sort_string.split(";")
		_, sort_by  = sort_by.split("=")
		_, order = order.split("=")

		# Default options for the buttons on directory browser, that we set
		#  based on what we sorted by
		n_order_ascending = True
		m_order_ascending = True
		s_order_ascending = True
		d_order_ascending = True

		# Split dirs and files so we can sort dirs first
		dirs = [i for i in items if i.is_dir]
		files = [i for i in items if not i.is_dir]
		items = []

		# Sort the items, and update the relevant button to be opposite order
		reversed_order = (order == "D")
		if sort_by == "N":
			dirs = sorted(dirs, key=lambda i:i.name, reverse=reversed_order)
			files = sorted(files, key=lambda i:i.name, reverse=reversed_order)
			items = dirs + files
			n_order_ascending = reversed_order

		elif sort_by == "M":
			dirs = sorted(dirs, key=lambda i:i.name, reverse=reversed_order) # Cant sort
			files = sorted(files, key=lambda i:i.last_modified, reverse=reversed_order)
			items = dirs + files
			m_order_ascending = reversed_order

		elif sort_by == "S":
			dirs = sorted(dirs, key=lambda i:i.name, reverse=reversed_order) # Cant sort
			files = sorted(files, key=lambda i:i.size, reverse=reversed_order)
			items = dirs + files
			s_order_ascending = reversed_order
		
		elif sort_by == "D":
			dirs = sorted(dirs, key=lambda i:(i.description,i.name), reverse=reversed_order)
			files = sorted(files, key=lambda i:(i.description,i.name), reverse=reversed_order)
			items = dirs + files
			d_order_ascending = reversed_order


		header = f"""
		<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 3.2 Final//EN">
		<html>
		<head>
			<title>Index of /{path.rstrip("/")}</title>
		</head>
		<body>
		<h1>Index of /{path.rstrip("/")}</h1>
		"""

		table_start = f"""
		<table>
			<tr>
				<th valign="top"><img src="/icons/blank.gif" alt="[ICO]"></th>
				<th><a href="?C=N;O={"A" if n_order_ascending else "D"}">Name</a></th>
				<th><a href="?C=M;O={"A" if m_order_ascending else "D"}">Last modified</a></th>
				<th><a href="?C=S;O={"A" if s_order_ascending else "D"}">Size</a></th>
				<th><a href="?C=D;O={"A" if d_order_ascending else "D"}">Description</a></th>
			</tr>
			<tr>
				<th colspan="5"><hr></th>
			</tr>
		"""

		parent_dir = f"""
			<tr>
				<td valign="top"><img src="/icons/back.gif" alt="[PARENTDIR]"></td>
				<td><a href="{parent_dir_path}">Parent Directory</a></td>
				<td>&nbsp;</td>
				<td align="right">  - </td>
				<td>&nbsp;</td>
			</tr>
		"""

		item_rows = ""
		for item in items:
			if item.is_dir:
				item_rows += f"""
					<tr>
						<td valign="top"><img src="/icons/folder.gif" alt="[DIR]"></td>
						<td><a href="{item.path}">{item.name}</a></td>
						<td align="right">  - </td>
						<td align="right">  - </td>
						<td>&nbsp;</td>
					</tr>
				"""
			else:
				item_rows += f"""
					<tr>
						<td valign="top"><img src="/icons/sound2.gif" alt="[SND]"></td>
						<td><a href="{item.path}">{item.name}</a></td>
						<td align="right">{item.last_modified.strftime('%Y-%m-%d %H:%M')}  </td>
						<td align="right">{_bytes_to_readable(item.size)}</td>
						<td>&nbsp;</td>
					</tr>
				"""

		footer = """
			<tr>
				<th colspan="5"><hr></th>
			</tr>
		</table>
		<address>Bimpsonshare/1.0.0 (Ubuntu) Server</address>
		</body>
		</html>
		"""

		return header + table_start + parent_dir + item_rows + footer



def lambda_handler(event, context):
	resp = PathHandler()(event)
	return resp
