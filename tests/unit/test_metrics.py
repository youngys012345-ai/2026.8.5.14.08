from src.metrics.segmentation import (
    f1_at_iou,
    frame_accuracy,
    levenstein,
    sequence_edit_distance,
)


def test_frame_accuracy_perfect():
    assert frame_accuracy([0, 1, 1], [0, 1, 1]) == 1.0


def test_edit_and_f1():
    gt = [0, 0, 1, 1, 1, 2, 2]
    pred = [0, 0, 1, 1, 2, 2, 2]
    assert levenstein(pred, gt) > 0
    assert 0.0 <= f1_at_iou(pred, gt, 0.5) <= 1.0


def test_sequence_edit():
    assert sequence_edit_distance(["a", "b"], ["a", "b"]) == 0.0
    assert sequence_edit_distance(["a"], ["a", "b"]) > 0
