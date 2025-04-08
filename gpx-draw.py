#!/usr/bin/python3

import os
import sys
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
import xml.etree.ElementTree as ET
import math

def parse_gpx(file_path):
    """Parse GPX file and return lists of latitudes and longitudes."""
    tree = ET.parse(file_path)
    root = tree.getroot()
    ns = {'gpx': 'http://www.topografix.com/GPX/1/1'}
    lats, lons = [], []
    for trkpt in root.findall('.//gpx:trkpt', ns):
        lats.append(float(trkpt.get('lat')))
        lons.append(float(trkpt.get('lon')))
    return lats, lons

def plot_gpx_to_image(folder_path, output_filename='output.png', resolution=(512, 512), bbox=None):
    """Plot GPX paths from the folder onto an image."""
    fig, ax = plt.subplots(figsize=(resolution[0] / 100, resolution[1] / 100), dpi=100)
    ax.set_facecolor('white')
    
    for filename in os.listdir(folder_path):
        if filename.endswith('.gpx'):
            file_path = os.path.join(folder_path, filename)
            lats, lons = parse_gpx(file_path)
            if lats and lons:
                ax.plot(lons, lats, 'k-', linewidth=1)  # Draw path with black lines
    
    if bbox:
        ax.set_xlim(bbox[0], bbox[1])
        ax.set_ylim(bbox[2], bbox[3])
        ax.add_patch(Rectangle((bbox[0], bbox[2]), bbox[1] - bbox[0], bbox[3] - bbox[2], 
                               linewidth=1, edgecolor='black', facecolor='none'))
    
    ax.set_xlabel('Longitude')
    ax.set_ylabel('Latitude')
    # ax.invert_yaxis()  # To match typical latitude/longitude plotting
    
    # Save the figure directly to a file
    fig.savefig(output_filename, format='png')
    plt.close(fig)  # Close the figure to free memory
    
    print(f"Image saved as {output_filename}")

def autoscale_resolution_from_bbox(bbox, target_height):
    """Compute resolution from bbox and target height using average latitude."""
    if not bbox or len(bbox) != 4:
        raise ValueError("Bounding box must be provided with four values: min_lon, max_lon, min_lat, max_lat.")
    min_lat, max_lat = bbox[2], bbox[3]
    avg_lat = (min_lat + max_lat) / 2.0
    scale_factor = math.cos(math.radians(avg_lat))
    width = int(target_height * scale_factor)
    return (target_height, width)

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Plot GPX paths to an image.')
    parser.add_argument('folder_path', type=str, help='Path to the folder containing GPX files.')
    parser.add_argument('--output', type=str, default='output.png', help='Output image filename.')
    parser.add_argument('--resolution', type=int, nargs=2, default=[512, 512], help='Output image resolution (width height).')
    parser.add_argument('--bbox', type=float, nargs=4, help='Bounding box (min_lon, max_lon, min_lat, max_lat).')
    parser.add_argument('--autoscale', type=int, help='Target image height in pixels. Width is calculated by latitude. Requires --bbox.')
    
    args = parser.parse_args()
    
    if args.autoscale:
        resolution = autoscale_resolution_from_bbox(args.bbox, args.autoscale)
    elif args.resolution:
        resolution = tuple(args.resolution)
    
    plot_gpx_to_image(args.folder_path, args.output, resolution, args.bbox)
