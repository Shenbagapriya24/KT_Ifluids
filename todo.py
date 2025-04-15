# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

import json
import os
import boto3
import botocore
from boto3.dynamodb.conditions import Key
from boto3.dynamodb.conditions import Attr

# Prepare DynamoDB client
Todos_Table = os.getenv('TodosTable', None)
dynamodb = boto3.resource('dynamodb')
ddbTable = dynamodb.Table(Todos_Table)

def getItemFromDB(task_id):
    ddb_response = ddbTable.get_item(
        Key={'task_id': task_id}
    )    
    if 'Item' in ddb_response:
        response_body = ddb_response['Item']
    else:
        response_body = {}
    status_code = 200
    return response_body, status_code

def lambda_handler(event, context):
    route_key = f"{event['httpMethod']} {event['resource']}"  

    table_task_id = ddbTable.scan(ProjectionExpression = 'task_id') #ProjectionExpression is for fetching columns
    ret_task_id = [item['task_id'] for item in table_task_id.get('Items',[])]
    new_task_id = max(int(task_id) for task_id in ret_task_id) + 1
    print("new_task_id",new_task_id)

    if event['pathParameters'] is None or event['pathParameters']['task_id'] is None:
        print("task_id is not in the request")
        task_id = str(new_task_id)
    else:
        task_id = event['pathParameters']['task_id']
        print("task_id",event['pathParameters']['task_id']) 

    # Set default response, override with data from DynamoDB if any
    response_body = {'Message': 'Unsupported route'}
    status_code = 400
    headers = {
        'Content-Type': 'application/json',
        'Access-Control-Allow-Origin': '*',
        }

    try:
        # Get a list of all Users       
        if route_key == 'GET /todos':
            ddb_response = ddbTable.scan(Select='ALL_ATTRIBUTES') 
            # return list of items instead of full DynamoDB response
            response_body = ddb_response['Items']
            status_code = 200

        # Read a user by ID
        if route_key == 'GET /todos/{task_id}':
            response_body , status_code = getItemFromDB(task_id)
        
        # Delete a user by ID
        if route_key == 'DELETE /todos/{task_id}':
            # delete item in the database
            ddbTable.delete_item(
                Key={'task_id': event['pathParameters']['task_id']}
            )
            response_body = {'message':'Task deleted successfully'}
            status_code = 200
        
        # Create a new user 
        if route_key == 'POST /todos':
            task_id = str(new_task_id) 
            request_json = json.loads(event['body']) if event.get('body') else {}                       
            title = request_json['title']
            description = request_json['description']
            status = "Pending"

            ddb_item = {
                'task_id': task_id,
                'title': title,
                'description': description,
                'status': status,                
            }
            #ddb_item = json.loads(json.dumps(ddb_item))            
            ddbTable.put_item(Item=ddb_item)
            response_body , status_code = getItemFromDB(task_id)    
                 

        # Update a specific user by ID
        if route_key == 'PUT /todos/{task_id}':            
            request_json = json.loads(event['body']) if event.get('body') else {}
            task_id = task_id
            title = request_json['title']
            description = request_json['description']
            status = request_json['status']
            
            ddb_item = {                
		                'task_id': task_id,   
                        'title': title,
                        'description': description,
                        'status': status 
                    }
                        
            
            try:
                ddbTable.put_item(Item=ddb_item,ConditionExpression=Attr('title').not_exists() & Attr('task_id').not_exists())
                print("Executed Table query")
                response_body , status_code = getItemFromDB(task_id)

            except botocore.exceptions.ClientError as e:
                if e.response['Error']['Code'] == 'ConditionalCheckFailedException':
                    print("Title with this task_id already exists.")                    
                    response_body , status_code = getItemFromDB(task_id)

    except Exception as err:
        status_code = 400
        response_body = {'Error:': str(err)}
        print(str(err))
    return {
        'statusCode': status_code,
        'body': json.dumps(response_body),
        'headers': headers
    }