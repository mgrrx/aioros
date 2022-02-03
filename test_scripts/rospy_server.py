#!/usr/bin/python3

from genpy import message
import rospy
from std_srvs.srv import SetBool, SetBoolRequest, SetBoolResponse


def handle_server(req: SetBoolRequest):
    return SetBoolResponse(message=str(req.data), success=True)


rospy.init_node("test_server")
s = rospy.Service("set_bool", SetBool, handle_server)

rospy.spin()
