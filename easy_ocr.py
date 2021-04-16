from easyocr import Reader
import json
from scipy.ndimage.filters import median_filter
import cv2
import numpy as np
import pika
import sys
import signal
import base64
import consul
import threading
import re

from skimage.filters import unsharp_mask



def image_scale(image):
	scale = 1
	# load the input image from disk
	h, w, c = image.shape

	if (h > w):
		scale = 1920 / h
	else:
		scale = 1920 / w

	scale_percent = scale * 100  # percent of original size
	width = int(w * scale_percent / 100)
	height = int(h * scale_percent / 100)
	dim = (width, height)

	image = cv2.resize(image, dim)
	return image

def image_sharp(image, imgName):
	image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
	image = unsharp_mask(image, radius=6.8, amount=2.69)
	cv2.imwrite("images/{}dub.png".format(imgName), 255 * image)
	image = cv2.imread("images/{}dub.png".format(imgName))
	return image

def Easy_OCR_On_Image(img, threshold, imgName,labelName):
	image_scaled = image_scale(img)
	image_sharpened = image_sharp(image_scaled, imgName)
	img_rotate_180 = cv2.rotate(image_sharpened, cv2.ROTATE_180)

	print("[INFO] OCR'ing input image...")
	reader = Reader(['da'], gpu=False)
	results = reader.readtext(image_sharpened)
	results1 = reader.readtext(img_rotate_180)
	# loop over the results

	wordsInImg = []
	wordsInRotated = []
	probNorm = 0
	probRotated = 0

	for (bbox, text, prob) in results:
		probNorm = probNorm + prob
		if(prob > threshold):
			wordsInImg.append(text)

	for (bbox, text, prob) in results1:
		probRotated = probRotated + prob
		if(prob > threshold):
			wordsInRotated.append(text)

	if(probNorm > probRotated):
		return wordsInImg

	return wordsInRotated

#################################### TEMPLATE STAARTS ###############################################
import traceback
import json
import consul
import base64
import re
import cv2
import numpy as np
import pika
import sys
import signal
from datetime import datetime
from PIL import Image
from io import BytesIO



def queue_callback(ch, method, properties, body):
	##Reads
	body = body_handler(body.decode('UTF-8'), ch)
	output_publisher_handler(body, ch)
	##THIS IS THE FINAL ACKNOWLEDGEMENT TO RABBITMQ THAT THE MSG IS DONE
	ch.basic_ack(delivery_tag=method.delivery_tag)


def signal_handler(signal,frame):
  print("\nCTRL-C handler, cleaning up rabbitmq connection and quitting")
  sys.exit(0)


def body_handler(body, ch):
	try:
		print("Starting body handler")
		#Load the Whole json object
		jsonObject = json.loads(body)


		#Main Piece of code that handles the body payload per payload
		for payloadCount in jsonObject["Payload"]:
			payload = jsonObject["Payload"][payloadCount]
			payload_Handler(payload)

		#KEEP AT THE BOTTOM, HANDLES CONSUMING AND LOGGING
		log_publisher_handler(jsonObject,"Succes", ch)
		# log_publisher_handler(jsonObject,"SUCCESFUL")
		return json.dumps(jsonObject)

	except:
		log_publisher_handler('ERROR IN INITIAL SETUP', traceback.print_exc(), ch)
		# log_publisher_handler(jsonObject, sys.exc_info()[0])
def payload_Handler(payloadString):
	#CHANGED FOR EACH SERVICE
	imageEncoded = payloadString["ImageEncoded"]
	img = decode_base64_toImage(imageEncoded)
	print(payloadString['ImageName'],payloadString['Type'])
	results = Easy_OCR_On_Image(img,0.3,payloadString['ImageName'],payloadString['Type'])
	word = ""
	for x in results:
		word = word + "%/%" + x

	payloadString['WordsInPicture'] = word
	return payloadString
def commandqueue_handler():
	credentials = pika.PlainCredentials("guest", "guest")
	connection = pika.BlockingConnection(pika.ConnectionParameters(RabbitMqIp, int(RabbitMqPort), '/'))
	channel = connection.channel()

	channel.basic_consume(queue=CommandQueue, on_message_callback=commandqueue_callback)

	channel.start_consuming()

#Command queue Handler
def commandqueue_callback(ch, method, properties, body):
	##Reads
	print(body, 'COMMANDQUEUE')
	##THIS IS THE FINAL ACKNOWLEDGEMENT TO RABBITMQ THAT THE MSG IS DONE
	ch.basic_ack(delivery_tag=method.delivery_tag)

def output_publisher_handler(jsonObject, channel):
	print(jsonObject)
	channel.basic_publish(exchange='', routing_key=Service_Output, body=jsonObject)

def log_publisher_handler(jsonObject,additionalMessaage, channel):
	jsonObject["Additional"] = additionalMessaage
	jsonObject["Timestamp"] = time_stamp()
	jsonObject["ServerInfo"] = "Inserting at a later point"
	jsonMessage = json.dumps(jsonObject)
	channel.basic_publish(exchange='', routing_key=LogQueue, body=jsonMessage)
def time_stamp():
	now = datetime.now()
	current_time = now.strftime("%d/%m/%Y %H:%M:%S")
	return current_time
def server_stamp():
	waitingforNomad = "False"
	return waitingforNomad
def decode_base64_toImage(data):
	image_string = data
	img_data = base64.b64decode(image_string)
	nparr = np.frombuffer(img_data, np.uint8)
	img_np = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
	return img_np
def Consuming(ch):
	print("Starting Input Queue Handler")

		# capture CTRL-C
	signal.signal(signal.SIGINT, signal_handler)

	print("Waiting for messages, CTRL-C to quit...")
	channel.start_consuming()

try:
	c = consul.Consul()

	## Define the Name of the current service
	ServiceName = 'OCR'
	##Inserted co Infront of objects loaded from consul to mark them as a Consul Object
	mqIndex, coRabbitMq_Settings = c.kv.get('RabbitMq_Settings')
	coRabbitMq_Settings['Value'] = coRabbitMq_Settings['Value'].decode("utf-8")
	RabbitMq_Settings = json.loads(coRabbitMq_Settings['Value'])

	##Getting all the queues for the specific service.
	Service_Input = RabbitMq_Settings['RabbitMq_Queues'][ServiceName+"_Input"]
	Service_Output = RabbitMq_Settings['RabbitMq_Queues'][ServiceName+"_Output"]
	Service_Unprocessed = RabbitMq_Settings['RabbitMq_Queues'][ServiceName+"_Unprocessed"]
	CommandQueue = RabbitMq_Settings['RabbitMq_Queues']["CommandQueue"]
	LogQueue = RabbitMq_Settings['RabbitMq_Queues']["LogQueue"]
	RabbitMqIp = RabbitMq_Settings['RabbitMq_Settings']['RabbitmqIp']
	RabbitMqPort = int(RabbitMq_Settings['RabbitMq_Settings']['Rabbitmqport'])

	queuenames = [Service_Input, Service_Output, Service_Unprocessed, CommandQueue, LogQueue, RabbitMqIp, RabbitMqPort]

	print(queuenames)

	credentials = pika.PlainCredentials("guest", "guest")
	connection = pika.BlockingConnection(pika.ConnectionParameters(RabbitMqIp, RabbitMqPort, '/'))
	channel = connection.channel()

	channel.basic_consume(queue=Service_Input, on_message_callback=queue_callback)
	cmThread = threading.Thread(target=commandqueue_handler)
	cmThread.start()
	Consuming(channel)
except:
	try:
		log_publisher_handler('ERROR IN INITIAL SETUP', traceback.print_exc(), channel)
	except:
		credentials = pika.PlainCredentials("guest", "guest")
		connection = pika.BlockingConnection(pika.ConnectionParameters(RabbitMqIp, RabbitMqPort, '/'))
		channel = connection.channel()
		log_publisher_handler('ERROR IN INITIAL SETUP', traceback.print_exc(),channel)





########################### TEMPLATE ENDS ####################################

# def Easy_OCR_On_Document(img, threshold, imgName, labelName):
# 	# pytesseract.pytesseract.tesseract_cmd = 'C:\\Program Files (x86)\\Tesseract-OCR\\tesseract.exe'
# 	image_sharpened = image_sharp(img, imgName)
# 	img_rotate_180 = cv2.rotate(image_sharpened, cv2.ROTATE_180)
#
# 	# TemplateBBs = LoadBoundingBoxFromDB(labelName)
#     # SKAL OMSKRIVES NÅR LOGGING KOMMER PÅ PLADS
# 	wordsInImg = []
# 	wordsInRotated = []
# 	probNorm = 0
# 	probRotated = 0
#
#
# 	print("[INFO] OCR'ing input image...")
# 	reader = Reader(['da'], gpu=True)
# 	# loop over the results
#
# 	for TemplateBB in TemplateBBs:
# 		(x, y, w, h) = TemplateBB.xMin,TemplateBB.yMin, TemplateBB.xMax-TemplateBB.xMin,TemplateBB.yMax-TemplateBB.yMin
#
# 		roi = img[y:y + h, x:x + w]
#
# 		rgb = cv2.cvtColor(roi, cv2.COLOR_BGR2RGB)
# 		results = reader.readtext(rgb)
#
# 		for (bbox, text, prob) in results:
# 			probNorm = probNorm + prob
# 			if (prob > threshold):
# 				item = {TemplateBB.description: text}
# 				wordsInImg.append(item)
#
# 		roi_180 = img_rotate_180[y:y + h, x:x + w]
# 		rgb_180 = cv2.cvtColor(roi_180, cv2.COLOR_BGR2RGB)
# 		results1 = reader.readtext(rgb_180)
#
# 		for (bbox, text, prob) in results1:
# 			probRotated = probRotated + prob
# 			if (prob > threshold):
# 				item = {TemplateBB.description: text}
# 				wordsInRotated.append(item)
#
#
#
#
# 	if(probNorm > probRotated):
# 		return json.dumps(wordsInImg,ensure_ascii=False)
#
# 	return json.dumps(wordsInRotated,ensure_ascii=False)

#
# TestImg = cv2.imread("C:/Users/LarsP/Desktop/yolov5/Installation/Form.png")
# Text  = Easy_OCR_On_Document(TestImg,0,"CoolName",'This is a Tt100')

def Replacement(text, valuetype):
	finalList = ''
	if(valuetype == "str"):
		for words in text.split():
			word = ''
			for chars in words:
				if (chars.isdigit()):
					if (chars == "1"):
						finalList = finalList + "i"
					elif (chars == "0"):
						finalList = finalList + "o"
				else:
					finalList = finalList + chars
			finalList = finalList + " "
	elif(valuetype == "int"):
		finalList = ''
		for words in text.split():
			word = ''
			for chars in words:
				if (chars.isalpha()):
					if (chars == "i" or chars == "I"):
						finalList = finalList + "1"
					elif (chars == "o" or chars == "O"):
						finalList = finalList + "0"
				else:
					finalList = finalList + chars
			finalList = finalList + " "
	elif(valuetype == "bth"):
		finalList = text
	return finalList

print("Hello World")
