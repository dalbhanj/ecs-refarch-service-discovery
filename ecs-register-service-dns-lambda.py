from __future__ import print_function

import json
import boto3

def lambda_handler(event, context):
  
  # spit out event data
	print("Received event: " + json.dumps(event, indent=2))    

	# private hosted zone domain name and id
	privatezone = 'ecs.internal'
	zoneid = 'Z21CIYIW8RPLL1'
	cluster = 'ecs-service-discovery-ECSCluster-ZE7FT679UUKV'

	# grab load balancer and service names
	tgArn = event['detail']['responseElements']['service']['loadBalancers'][0]['targetGroupArn']
	service = event['detail']['responseElements']['service']['serviceName']
	
	print("tgArn:", tgArn)
	print("Service name:", service)

	# check we are working against the appropriate ecs cluster
	if cluster != event['detail']['requestParameters']['cluster']:

		print("This event does not apply to us. No action taken.")
		return 0

	# grab DNS name for load balancer
	elbclient = boto3.client('elbv2')
	describealbtg = elbclient.describe_target_groups(
		TargetGroupArns=[
			tgArn
		]
	)
	print("describealbtg:", describealbtg)
	
	describealbArn = describealbtg['TargetGroups'][0]['LoadBalancerArns'][0]
	print("describealbArn:", describealbArn)
	
	describealbcanonical = elbclient.describe_load_balancers(
	    LoadBalancerArns=[
	        describealbArn
	    ]
	)
	albcanonical = describealbcanonical['LoadBalancers'][0]['DNSName']
	print("albcanonical:", albcanonical)
	servicerecord = service + "." + privatezone + "."

	# grab type of event
	eventname = event['detail']['eventName']

	# boto connect to route53
	route53client = boto3.client('route53')

	# create/update record
	if eventname == 'CreateService':

		response = route53client.change_resource_record_sets(
			HostedZoneId=zoneid,
			ChangeBatch={
				'Comment' : 'ECS service registered',
				'Changes' : [
					{
						'Action' : 'UPSERT',
						'ResourceRecordSet' : {
							'Name' : servicerecord,
							'Type' : 'CNAME',
							'TTL' : 60,
							'ResourceRecords' : [
								{
									'Value' : albcanonical
								}
							]
						}
					}
				] 
			}
		)

		print(response)

	# delete record
	elif eventname == 'DeleteService':

		response = route53client.change_resource_record_sets(
			HostedZoneId=zoneid,
			ChangeBatch={
				'Comment' : 'ECS service deregistered',
				'Changes' : [
					{
						'Action' : 'DELETE',
						'ResourceRecordSet' : {
							'Name' : servicerecord,
							'Type' : 'CNAME',
							'TTL' : 60,
							'ResourceRecords' : [
								{
									'Value' : albcanonical
								}
							]
						}
					}
				] 
			}
		)

		print(response)
		return response

	else:

			print("This event does not apply to us. No action taken.")
			return 0
