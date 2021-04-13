import consul
import json
import pika

c = consul.Consul()

ServiceNames = ['Database','OCR','Rotation','ImageDetector']

# for x in ServiceNames:
#     c.kv.put('{}_Input'.format(x),'{}_input'.format(x.lower()))
#     c.kv.put('{}_Output'.format(x), '{}_output'.format(x.lower()))
#     c.kv.put('{}_Unprocessed'.format(x), '{}_unprocessed'.format(x.lower()))
#
# c.kv.put('CommandQueue','commandqueue')
# c.kv.put('LogQueue','logqueue')
# c.kv.put('RabbitMqIp','localhost')
# c.kv.put('RabbitMqPort','5672')
#
ConsulSettings = {
   "RabbitMq_Settings":{
      "RabbitmqIp":"localhost",
      "Rabbitmqport":5672
   },
   "RabbitMq_Queues":{
      "Database_Input":"database_input",
      "Database_Output":"imagedetector_input",
      "Database_Unprocessed":"database_unprocessed",
      "OCR_Input":"ocr_input",
      "OCR_Output":"database_input",
      "OCR_Unprocessed":"ocr_unprocessed",
      "Rotation_Input":"rotation_input",
      "Rotation_Output":"ocr_input",
      "Rotation_Unprocessed":"rotation_unprocessed",
      "ImageDetector_Input":"imagedetector_input",
      "ImageDetector_Output":"rotation_input",
      "ImageDetector_Unprocessed":"imagedetector_unprocessed",
      "CommandQueue":"commandqueue",
      "LogQueue":"logqueue"
   }
}
c.kv.put('RabbitMq_Settings',json.dumps(ConsulSettings))

credentials = pika.PlainCredentials("guest", "guest")
connection = pika.BlockingConnection(pika.ConnectionParameters('localhost', 5672, '/'))
channel = connection.channel()

for x in ServiceNames:
    channel.queue_declare(queue='{}_input'.format(x.lower()))
    channel.queue_declare(queue='{}_unprocessed'.format(x.lower()))

channel.queue_declare(queue='commandqueue')
channel.queue_declare(queue='logqueue')
