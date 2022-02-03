#!/usr/bin/env python3

import logging
from itertools import count

import rospy
from std_msgs.msg import String


def main() -> None:
    rospy.init_node("test_publisher")
    pub = rospy.Publisher("/chatter", String, queue_size=10)
    counter = count()
    while not rospy.is_shutdown():
        msg = String(f"Message {next(counter)}")
        pub.publish(msg)
        rospy.sleep(0.00001)


if __name__ == "__main__":
    main()
