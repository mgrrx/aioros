from abc import ABCMeta, abstractmethod
from functools import singledispatch
from typing import Optional, Protocol

from genpy import Duration, Time
from geometry_msgs.msg import (
    Point,
    PointStamped,
    Pose,
    PoseStamped,
    Quaternion,
    TransformStamped,
    Vector3,
    Vector3Stamped,
    Wrench,
    WrenchStamped,
)
from sensor_msgs.msg import PointCloud2

from ..abc import MessageWithHeaderT
from ._linear_math import Quaternion as CQuaternion
from ._linear_math import Transform as CTransform
from ._linear_math import Vector3 as CVector3


class Vector3Like(Protocol):
    x: float
    y: float
    z: float


class QuaternionLike(Protocol):
    x: float
    y: float
    z: float
    w: float


def to_quaternion(rotation: QuaternionLike) -> CQuaternion:
    return CQuaternion(rotation.x, rotation.y, rotation.z, rotation.w)


def to_vector3(vector: Vector3Like) -> CVector3:
    return CVector3(vector.x, vector.y, vector.z)


@singledispatch
def do_transform(
    message: MessageWithHeaderT, transform_stamped: TransformStamped
) -> MessageWithHeaderT:
    raise TypeError()


# PointStamped
def do_transform_point(
    message: PointStamped, transform_stamped: TransformStamped
) -> PointStamped:
    point = (
        CTransform(
            to_quaternion(transform_stamped.transform.rotation),
            to_vector3(transform_stamped.transform.translation),
        )
        @ to_vector3(message.point)
    )
    return PointStamped(
        header=transform_stamped.header,
        point=Point(x=point.x, y=point.y, z=point.z),
    )


def do_transform_vector3(
    message: Vector3Stamped, transform_stamped: TransformStamped
) -> Vector3Stamped:
    point = (
        CTransform(
            to_quaternion(transform_stamped.transform.rotation),
            CVector3(0.0, 0.0, 0.0),
        )
        @ to_vector3(message.vector)
    )
    return Vector3Stamped(
        header=transform_stamped.header,
        vector=Vector3(x=point.x, y=point.y, z=point.z),
    )


# PoseStamped
def do_transform_pose(
    message: PoseStamped, transform_stamped: TransformStamped
) -> PoseStamped:
    transform = CTransform(
        to_quaternion(transform_stamped.transform.rotation),
        to_vector3(transform_stamped.transform.translation),
    ) @ CTransform(
        to_quaternion(message.pose.orientation),
        to_vector3(message.pose.position),
    )
    return PoseStamped(
        header=transform_stamped.header,
        pose=Pose(
            position=Point(
                x=transform.translation.x,
                y=transform.translation.y,
                z=transform.translation.z,
            ),
            orientation=Quaternion(
                x=transform.rotation.x,
                y=transform.rotation.y,
                z=transform.rotation.z,
                w=transform.rotation.w,
            ),
        ),
    )


def do_transform_wrench(
    message: WrenchStamped, transform_stamped: TransformStamped
) -> TransformStamped:
    return WrenchStamped(
        header=transform_stamped.header,
        wrench=Wrench(
            force=do_transform_vector3(
                Vector3Stamped(vector=message.wrench.force), transform_stamped
            ).vector,
            torque=do_transform_vector3(
                Vector3Stamped(vector=message.wrench.torque), transform_stamped
            ).vector,
        ),
    )


def do_transform_cloud(
    message: PointCloud2, transform_stamped: TransformStamped
) -> TransformStamped:
    from sensor_msgs.point_cloud2 import create_cloud, read_points

    transform = CTransform(
        to_quaternion(transform_stamped.transform.rotation),
        to_vector3(transform_stamped.transform.translation),
    )

    points_out = []
    for p_in in read_points(message):
        p_out = transform @ CVector3(p_in[0], p_in[1], p_in[2])
        points_out.append((p_out.x, p_out.y, p_out.z) + p_in[3:])
    return create_cloud(transform_stamped.header, message.fields, points_out)


do_transform.register(PointCloud2, do_transform_cloud)
do_transform.register(PointStamped, do_transform_point)
do_transform.register(PoseStamped, do_transform_pose)
do_transform.register(Vector3Stamped, do_transform_vector3)
do_transform.register(WrenchStamped, do_transform_wrench)


class BufferInterface(metaclass=ABCMeta):
    async def transform(
        self,
        object_stamped: MessageWithHeaderT,
        target_frame: str,
        timeout: Optional[Duration] = None,
    ) -> MessageWithHeaderT:
        return do_transform(
            object_stamped,
            await self.lookup_transform(
                target_frame,
                object_stamped.header.frame_id,
                object_stamped.header.stamp,
                timeout,
            ),
        )

    async def transform_full(
        self,
        object_stamped: MessageWithHeaderT,
        target_frame: str,
        target_time: Time,
        fixed_frame: str,
        timeout: Optional[Duration] = None,
    ) -> MessageWithHeaderT:
        return do_transform(
            object_stamped,
            await self.lookup_transform_full(
                target_frame,
                target_time,
                object_stamped.header.frame_id,
                object_stamped.header.stamp,
                fixed_frame,
                timeout,
            ),
        )

    @abstractmethod
    async def lookup_transform(
        self,
        target_frame: str,
        source_frame: str,
        time: Time,
        timeout: Optional[Duration] = None,
    ) -> TransformStamped:
        ...

    @abstractmethod
    async def lookup_transform_full(
        self,
        target_frame: str,
        target_time: Time,
        source_frame: str,
        source_time: Time,
        fixed_frame: str,
        timeout: Optional[Duration] = None,
    ) -> TransformStamped:
        ...

    @abstractmethod
    async def can_transform(
        self,
        target_frame: str,
        source_frame: str,
        time: Time,
        timeout: Optional[Duration] = None,
    ) -> bool:
        ...

    @abstractmethod
    async def can_transform_full(
        self,
        target_frame: str,
        target_time: Time,
        source_frame: str,
        source_time: Time,
        fixed_frame: str,
        timeout: Optional[Duration] = None,
    ) -> bool:
        ...
