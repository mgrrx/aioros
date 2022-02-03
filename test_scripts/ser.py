from io import BytesIO

from geometry_msgs.msg._PoseWithCovarianceStamped import (
    PoseWithCovarianceStamped,
    _get_struct_3I,
    _get_struct_7d,
    _get_struct_36d,
    _struct_I,
)

msg = PoseWithCovarianceStamped()
msg.header.frame_id = "foo"
msg.header.stamp.secs = 13
msg.header.stamp.nsecs = 37
msg.pose.covariance = [float(i) for i in range(36)]
msg.pose.pose.position.x = 50.0
msg.pose.pose.position.y = 60.0
msg.pose.pose.position.z = 70.0
msg.pose.pose.orientation.x = -10.0
msg.pose.pose.orientation.y = -20.0
msg.pose.pose.orientation.z = -30.0
msg.pose.pose.orientation.w = -40.0

b = BytesIO()
msg.serialize(b)

data = b.getvalue()


def old():
    m = PoseWithCovarianceStamped()
    m.deserialize(data)
    return m


def new():
    v = memoryview(data)
    m = PoseWithCovarianceStamped()
    m.header.seq, m.header.stamp.secs, m.header.stamp.nsecs = v[0:12].cast("I")
    frame_id_end = v[12:16].cast("I")[0] + 16
    pose_end = frame_id_end + 56
    m.header.frame_id = v[16:frame_id_end].tobytes().decode("utf-8", "rosmsg")
    (
        m.pose.pose.position.x,
        m.pose.pose.position.y,
        m.pose.pose.position.z,
        m.pose.pose.orientation.x,
        m.pose.pose.orientation.y,
        m.pose.pose.orientation.z,
        m.pose.pose.orientation.w,
    ) = v[frame_id_end:pose_end].cast("d")
    m.pose.covariance = list(v[pose_end : (pose_end + 288)].cast("d"))
    return m


from timeit import timeit

print(old() == new())

print(timeit(old) / 1000000.0)
print(timeit(new) / 1000000.0)
