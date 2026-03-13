import io
import logging
import os
from PIL import Image, ImageDraw, ImageFont
from dataclasses import dataclass

from core.models.sensor_enum import SensorId
from core.config_loader import config_loader

logger = logging.getLogger(__name__)

@dataclass
class GraphiqueConfig:
    width: int = 1100
    height: int = 1100
    margin: int = 85
    axis_color: str = 'black'
    axis_width: int = 4
    x_min: float = 0
    y_min: float = 0
    line_color: str = 'black'
    line_width: int = 4
    x_tick_interval: int = 2
    y_tick_interval: int = 200
    tick_size: int = 10
    font_size: int = 34
    small_font_size: int = 22
    text_color: str = 'black'
    label_spacing: int = 10
    
class Graphique:
    """
    Manages the graphical representation of sensor data, including plotting points on the force-displacement and force-arc graphiques.
    """
    def __init__(self, Xsensor: SensorId, Ysensor: SensorId, config: GraphiqueConfig):
        
        self.Xsensor = Xsensor
        self.Ysensor = Ysensor
        self.config = config 
        
        self.image: Image.Image = Image.new('RGBA', (self.config.width, self.config.height), (255, 255, 255, 0))
        self.draw: ImageDraw.ImageDraw = ImageDraw.Draw(self.image)
        self.last_point: tuple[float, float] = (0,0)
        
        self.Xsensor_config = config_loader.get_sensor_config(self.Xsensor)
        self.Ysensor_config = config_loader.get_sensor_config(self.Ysensor)
        
        # Try to use a default font, fall back to default if not available
        try:
            self.font = ImageFont.truetype("../fonts/DejaVuSans-Bold.ttf", self.config.font_size)
            self.font_small = ImageFont.truetype("../fonts/DejaVuSans.ttf", self.config.small_font_size)
        except:
            self.font = ImageFont.load_default(size=self.config.font_size)
            self.font_small = ImageFont.load_default(size=self.config.small_font_size)

        self.draw_graphique_axes()

    def reset(self):
        self.image = Image.new('RGBA', (self.config.width, self.config.height), (255, 255, 255, 0))
        self.draw = ImageDraw.Draw(self.image)
        self.last_point = (0,0)
        self.draw_graphique_axes()
        
    def draw_graphique_axes(self):
        x_label = f"{self.Xsensor_config.displayName}"
        y_label = f"{self.Ysensor_config.displayName}"
        
        x_max = self.Xsensor_config.max
        x_min = self.config.x_min
        x_range = x_max - x_min
        y_max = self.Ysensor_config.max
        y_min = self.config.y_min
        y_range = y_max - y_min
        
        axis_color = self.config.axis_color
        axis_width = self.config.axis_width
        text_color = self.config.text_color
        tick_size = self.config.tick_size
        
        # X axis (bottom)
        # Draw axis line
        x_axis_y = self.config.height - self.config.margin
        self.draw.line(
            [(self.config.margin, x_axis_y), 
             (self.config.width - self.config.margin, x_axis_y)],
            fill=axis_color,
            width=axis_width
        )
        
        # Draw X axis label centered below the axis
        xlabel_w = self.font.getlength(x_label)
        xlabel_x = self.config.width - self.config.margin - xlabel_w - 20
        self.draw.text(
            (xlabel_x, self.config.height - self.config.margin + 40),
            x_label,
            fill=text_color,
            font=self.font
        )
        
        # Draw X axis ticks and labels
        for x_val in range(int(x_min), int(x_max) + 1, self.config.x_tick_interval):
            # Map x_val to pixel position
            pixel_x = self.config.margin + ((x_val - x_min) / x_range) * (self.config.width - 2 * self.config.margin)
            # Draw tick
            self.draw.line(
                [(pixel_x, x_axis_y), (pixel_x, x_axis_y + tick_size)],
                fill=axis_color,
                width=axis_width
            )
            
            label = str(x_val)
            text_w = self.font_small.getlength(label)
            label_x = pixel_x - (text_w / 2)
            # Clamp so text stays inside left/right margins
            min_x = self.config.margin
            max_x = self.config.width - self.config.margin - text_w
            label_x = max(min_x, min(max_x, label_x))
            self.draw.text(
                (label_x, x_axis_y + tick_size + self.config.label_spacing),
                label,
                fill=text_color,
                font=self.font_small
            )
            

        # Y axis (left)
        y_axis_x = self.config.margin + 30
        self.draw.line(
            [(y_axis_x, self.config.margin), 
             (y_axis_x, self.config.height - self.config.margin)],
            fill=axis_color,
            width=axis_width
        )
        
        # Draw Y axis label
        self.draw.text(
            (15, 10),
            y_label,
            fill=text_color,
            font=self.font
        )
        
        # Draw Y axis ticks and labels
        for y_val in range(int(y_min), int(y_max) + 1, self.config.y_tick_interval):
            # Map y_val to pixel position
            pixel_y = self.config.height - self.config.margin - (y_val / y_max) * (self.config.height - 2 * self.config.margin)
            # Draw tick
            self.draw.line(
                [(y_axis_x - tick_size, pixel_y), (y_axis_x, pixel_y)],
                fill=axis_color,
                width=3
            )
            # Draw label
            label = str(y_val)
            text_w = self.font_small.getlength(label)
            self.draw.text(
                (y_axis_x - text_w - self.config.label_spacing, 
                 pixel_y - (self.config.small_font_size // 2)),
                label,
                fill=text_color,
                font=self.font_small
            )
            
    def plot_point_on_graphique(self, x_value: float, force: float):
        
        if self.draw is None:
            return
        
        # Scaling parameters (force range from config)
        y_max = self.Ysensor_config.max
        x_max = self.Xsensor_config.max
        x_min = self.config.x_min
        x_range = x_max - x_min
        
        # Convert data to pixel coordinates
        # X axis: left margin to right margin
        pixel_x = self.config.margin + ((x_value - x_min) / x_range) * (self.config.width - 2 * self.config.margin)
        # Y axis: inverted (top is 0, bottom is max)
        pixel_y = self.config.height - self.config.margin - (force / y_max) * (self.config.height - 2 * self.config.margin)
        
        current_point = (pixel_x, pixel_y)
        
        if self.last_point != (0,0):
            # Draw line from last point to current point
            if self.last_point is not None:
                self.draw.line(
                    [self.last_point, current_point],
                    fill=self.config.line_color,
                    width=self.config.line_width
                )

        self.last_point = current_point
        
    def save_graphique(self, directory: str|None, filename: str):
        if directory is None:
            logger.warning("Cannot save graphiques: no test directory")
            return
        
        # Save DISP_1 graphique
        if self.image is not None:
            disp1_path = os.path.join(directory, filename)
            try:
                self.image.save(disp1_path, format='PNG')
                logger.info(f"Saved DISP_1 graphique to {disp1_path}")
            except Exception as e:
                logger.error(f"Failed to save DISP_1 graphique: {e}")
                
                
    def get_graphique_png(self) -> bytes:
               
        if self.image is None:
            # Return a blank canvas if no test running
            image = Image.new('RGBA', (self.config.width, self.config.height), (255, 255, 255, 0))
        
        # Convert to PNG bytes
        buffer = io.BytesIO()
        self.image.save(buffer, format='PNG')
        return buffer.getvalue()
        
        