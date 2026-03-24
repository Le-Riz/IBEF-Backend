from dataclasses import asdict
import logging
import json
import math
import os
import csv
from PIL import Image, ImageDraw, ImageFont

from core.models.test_data import TestMetaData

logger = logging.getLogger(__name__)

class TreatmentModule:
    #Please leave the extension as png for the image or otherwise change the format output
    image_name = "treatment_image.png"
    json_name = "treatments.json"
    
    def __init__(self, directory: str):
        self.directory = directory
        self.datas: list[dict[str, float]] = []
        self.metadata: dict[str, str|float] = {}
        
        self.image: Image.Image = Image.new('RGBA', (1100, 1100), (255, 255, 255, 0))
        self.draw = ImageDraw.Draw(self.image)
        self.font = ImageFont.load_default(size=25)
        
        self.output_json: dict[str, str] = {"data 1" : "", 
                                            "data 2": ""}
        
        
    def load_data(self, csv_file: str) -> None:
        """Load data from the specified directory"""
        logger.info(f"Loading data from {csv_file}...")
        csv_path = open(os.path.join(self.directory, csv_file), 'r')
        reader = csv.DictReader(csv_path)
        for row in reader:
            timestamp = math.nan if row["timestamp"] == "" else float(row["timestamp"])
            relative_time = math.nan if row["relative_time"] == "" else float(row["relative_time"])
            arc = math.nan if row["ARC"] == "" else float(row["ARC"])
            disp_1 = math.nan if row["DISP_1"] == "" else float(row["DISP_1"])
            disp_2 = math.nan if row["DISP_2"] == "" else float(row["DISP_2"])
            disp_3 = math.nan if row["DISP_3"] == "" else float(row["DISP_3"])
            disp_4 = math.nan if row["DISP_4"] == "" else float(row["DISP_4"])
            disp_5 = math.nan if row["DISP_5"] == "" else float(row["DISP_5"])
            force = math.nan if row["FORCE"] == "" else float(row["FORCE"])
            
            data_line = {"timestamp": timestamp, 
                         "relative_time": relative_time,
                         "ARC": arc,
                         "DISP_1": disp_1,
                         "DISP_2": disp_2,
                         "DISP_3": disp_3,
                         "DISP_4": disp_4,
                         "DISP_5": disp_5,
                         "FORCE": force}
        
            self.datas.append(data_line)
        csv_path.close()
        
    def load_metadata(self, metadata: TestMetaData) -> None:
        """Load metadata from the specified dictionary"""
        logger.info("Loading metadata...")
        self.metadata = asdict(metadata)
    
    def save_output(self) -> None:
        """Save the processed output to a JSON file in the specified directory"""
        logger.info(f"Saving output to {self.directory}...")
        output_path = os.path.join(self.directory, self.json_name)
        with open(output_path, "w") as f:
            json.dump(self.output_json, f)
        
        # Change the format of the image if needed
        self.image.save(os.path.join(self.directory, self.image_name), format='PNG')

    def process_data(self) -> None:
        """Process the loaded data. This is a placeholder for the actual data processing logic."""
        logger.info("Processing data...")
        
        #################################################################################
        #                                                                               #
        #                   PLACE YOUR DATA PROCESSING LOGIC HERE                       #
        #                                                                               #
        #################################################################################
        # You can use self.datas to access the loaded data, which is a list of dictionaries with keys:
        # "timestamp", "relative_time", "ARC", "DISP_1", "DISP_2", "DISP_3", "DISP_4", "DISP_5", "FORCE"
        # You can store results in self.output_json and create an image using self.image and self.draw.


        # Example of data browsing:        
        count = 0
        for data in self.datas:
            
            if not math.isnan(data["DISP_1"]) and not math.isnan(data["FORCE"]):
                # Process the data of disp_1 and force
                count += 1
                
        self.output_json["data 1"] = f"Processed {count} valid data points for DISP_1 and FORCE."
        self.output_json["data 2"] = f"Total data points loaded for {self.metadata['specimen_code']}: {len(self.datas)}."
        
        self.draw.text((10, 10), self.output_json["data 1"], fill="black", font=self.font)
        self.draw.text((10, 40), self.output_json["data 2"], fill="black", font=self.font)
        
        
