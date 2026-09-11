import boto3

def lambda_handler(event, context):
    ec2 = boto3.client("ec2")

    # Get all EBS snapshots owned by this AWS account
    response = ec2.describe_snapshots(OwnerIds=["self"])

    # Get all currently running EC2 instances
    instances_response = ec2.describe_instances(
        Filters=[
            {
                "Name": "instance-state-name",
                "Values": ["running"]
            }
        ]
    )

    active_instance_ids = set()

    for reservation in instances_response["Reservations"]:
        for instance in reservation["Instances"]:
            active_instance_ids.add(instance["InstanceId"])

    # Check every EBS snapshot
    for snapshot in response["Snapshots"]:
        snapshot_id = snapshot["SnapshotId"]
        volume_id = snapshot.get("VolumeId")

        # Snapshot has no associated volume
        if not volume_id:
            ec2.delete_snapshot(SnapshotId=snapshot_id)

            print(
                f"Deleted EBS snapshot {snapshot_id} "
                "as it was not attached to any volume."
            )

            continue

        try:
            # Check whether the source volume still exists
            volume_response = ec2.describe_volumes(
                VolumeIds=[volume_id]
            )

            volume = volume_response["Volumes"][0]

            # Delete if the source volume has no attachment
            if not volume["Attachments"]:
                ec2.delete_snapshot(SnapshotId=snapshot_id)

                print(
                    f"Deleted EBS snapshot {snapshot_id} "
                    "as it was taken from a volume not attached "
                    "to any running instance."
                )

        except ec2.exceptions.ClientError as e:
            # Source volume no longer exists
            if e.response["Error"]["Code"] == "InvalidVolume.NotFound":
                ec2.delete_snapshot(SnapshotId=snapshot_id)

                print(
                    f"Deleted EBS snapshot {snapshot_id} "
                    "as its associated volume was not found."
                )
            else:
                raise
