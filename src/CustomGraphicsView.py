from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QGraphicsView


class CustomGraphicsView(QGraphicsView):
    def __init__(self, scene, parent_viewer):
        super().__init__(scene)
        self.parent_viewer = parent_viewer
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.AnchorUnderMouse)
        self.setViewportUpdateMode(QGraphicsView.FullViewportUpdate)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.setDragMode(QGraphicsView.ScrollHandDrag)
        self.setMouseTracking(True)

        # Set default arrow cursor
        self.setCursor(Qt.ArrowCursor)

    def mousePressEvent(self, event):
        # Change to hand cursor when dragging
        if event.button() == Qt.LeftButton:
            self.setCursor(Qt.ClosedHandCursor)
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        # Change back to arrow cursor when done dragging
        if event.button() == Qt.LeftButton:
            self.setCursor(Qt.ArrowCursor)
        super().mouseReleaseEvent(event)

    def mouseMoveEvent(self, event):
        super().mouseMoveEvent(event)
        mouse_pos = self.mapToScene(event.pos())
        x = int(mouse_pos.x())
        y = int(mouse_pos.y())
        self.parent_viewer.update_bottom_layers(x, y)

    def wheelEvent(self, event):
        factor = 1.1 if event.angleDelta().y() > 0 else 0.9
        self.scale(factor, factor)