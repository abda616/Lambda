import os
import boto3
import json
from datetime import datetime

session = boto3.Session(region_name = os.environ['region_name_is'])         # map to region
required_tags = {"aws:dlm:lifecycle-policy-id": os.environ['policy_id_is']} # map to policy_id
launch_template_id_is = os.environ['launch_template_id_is']                 # map to lanch_template



def has_tags(element, tags):                            # check if described-images has the desired tags
    element_tags = {tag['Key']: tag['Value'] for tag in element.get('Tags', [])}
    for key, value in tags.items():
        if element_tags.get(key) != value:
            return False
    return True


def parse_date(item):                                   # to check date formate it to be understand by 
    return datetime.fromisoformat(item["CreationDate"].replace("Z", "+00:00"))


def get_latest_ami_id():
    ec2_client = session.client('ec2')
    response = ec2_client.describe_images(                              # get AMI images
        Owners=['self']
    )
    data = response['Images']
    data = [element for element in data if has_tags(element, required_tags)]    # data without desiered tags will be removed 
    images = sorted(data, key=parse_date, reverse=True)                         # order the data based on time and reverse to find the most recent date
    return images[0]['ImageId'] if images else None                         


def create_launch_template_version(latest_ami_id, launch_template_id):
    ec2_client = session.client('ec2')
    describe_response = ec2_client.describe_launch_templates(   # get info about LT so I can find LatestVersionNumber -1->
        LaunchTemplateIds=[launch_template_id]
    )                                                   
    response = ec2_client.create_launch_template_version(           #create new version of LT
        LaunchTemplateId=launch_template_id,        
        SourceVersion=str(describe_response['LaunchTemplates'][0]['LatestVersionNumber']),  # -2->  to update it in next LT version
        LaunchTemplateData={
            'ImageId': latest_ami_id            # spicify AMI ID
        }
    )
    return response['LaunchTemplateVersion']['VersionNumber'] #retern VersionNumber of new LT


def update_launch_template(latest_ami_id, launch_template_id):
    ec2_client = session.client('ec2')
    response = ec2_client.modify_launch_template(           #update LT VersionN 
        LaunchTemplateId=launch_template_id,            
        DefaultVersion=str(create_launch_template_version(latest_ami_id, launch_template_id))  #update
    )
    return response


def lambda_handler(event, context):
    latest_ami_id = get_latest_ami_id()         # get ami if there is no ami ; Out else Countinue 
    if not latest_ami_id:
        return {
            'statusCode': 500,
            'body': json.dumps('No AMI found')
        }
    
                                                # start update LT and 
    response = update_launch_template(latest_ami_id, launch_template_id_is) 
    return {
        'statusCode': 200,
        'body': json.dumps(f'Launch template updated with AMI ID {latest_ami_id},version is {response["LaunchTemplate"]["LatestVersionNumber"]}')
    }
