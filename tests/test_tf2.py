import pytest
from geometry_msgs.msg import PointStamped, PoseStamped, TransformStamped

from aioros.tf2 import Buffer

pytestmark = pytest.mark.anyio


@pytest.fixture(name="tf_buffer")
def fixture_tf_buffer() -> Buffer:
    buffer = Buffer()
    transform = TransformStamped()
    transform.header.frame_id = "a"
    transform.child_frame_id = "b"
    transform.transform.translation.x = 1.0
    transform.transform.rotation.w = 1.0
    buffer.set_transform(transform, "pytest", is_static=True)
    return buffer


async def test_point_stamped(tf_buffer: Buffer) -> None:
    point = PointStamped()
    point.header.frame_id = "a"
    result = await tf_buffer.transform(point, "b")
    assert result.point.x == -1.0
    assert result.header.frame_id == "b"


async def test_pose_stamped(tf_buffer: Buffer) -> None:
    point = PoseStamped()
    point.header.frame_id = "a"
    result = await tf_buffer.transform(point, "b")
    assert result.pose.position.x == -1.0
    assert result.header.frame_id == "b"
