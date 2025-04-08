#!/usr/bin/python3

import os
import sys
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
import xml.etree.ElementTree as ET
import math
from datetime import datetime

def parse_gpx(file_path):
    """Parse GPX file and return list of (lat, lon, time) tuples."""
    tree = ET.parse(file_path)
    root = tree.getroot()
    ns = {'gpx': 'http://www.topografix.com/GPX/1/1'}
    points = []
    
    for trkpt in root.findall('.//gpx:trkpt', ns):
        lat = float(trkpt.get('lat'))
        lon = float(trkpt.get('lon'))
        time_elem = trkpt.find('gpx:time', ns)
        if time_elem is not None:
            time = datetime.fromisoformat(time_elem.text.replace("Z", "+00:00"))
            points.append((lat, lon, time))
    return points

def haversine(lat1, lon1, lat2, lon2):
    """Calculate great-circle distance in kilometers using the Haversine formula."""
    R = 6371.0  # Earth radius in kilometers
    
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    
    a = math.sin(dlat / 2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    
    return R * c

def compute_speed_kph(lat1, lon1, lat2, lon2, dt_seconds):
    """Return speed in km/h given two coordinates and time delta in seconds."""
    distance_km = haversine(lat1, lon1, lat2, lon2)
    hours = dt_seconds / 3600.0
    return abs(distance_km / hours) # Care about speed, not velocity, so abs value

def exceeds_speed_threshold(points, max_kph):
    """Check if any segment exceeds max speed in km/h."""
    for i in range(1, len(points)):
        lat1, lon1, t1 = points[i - 1]
        lat2, lon2, t2 = points[i]
        dt_seconds = (t2 - t1).total_seconds()
        if dt_seconds == 0:
            continue
        speed_kph = compute_speed_kph(lat1, lon1, lat2, lon2, dt_seconds)
        if speed_kph > max_kph:
            return True
    return False

def plot_gpx_to_image(folder_path, output_filename='output.png', resolution=(512, 512), bbox=None, max_speed=None):
    """Plot GPX paths from the folder onto an image."""
    fig, ax = plt.subplots(figsize=(resolution[0] / 100, resolution[1] / 100), dpi=100)
    ax.set_facecolor('white')
    
    for filename in os.listdir(folder_path):
        if filename.endswith('.gpx'):
            file_path = os.path.join(folder_path, filename)
            points = parse_gpx(file_path)
            if max_speed is not None and exceeds_speed_threshold(points, max_speed):
                print(f"Skipping {filename} (exceeds {max_speed} km/h)")
                continue
            lats, lons = zip(*[(p[0], p[1]) for p in points])
            ax.plot(lons, lats, 'k-', linewidth=0.5)  # Draw path with black lines
    
    if bbox:
        ax.set_xlim(bbox[0], bbox[1])
        ax.set_ylim(bbox[2], bbox[3])
        ax.add_patch(Rectangle((bbox[0], bbox[2]), bbox[1] - bbox[0], bbox[3] - bbox[2], 
                               linewidth=1, edgecolor='black', facecolor='none'))
    
    ax.set_xlabel('Longitude')
    ax.set_ylabel('Latitude')
    # ax.invert_yaxis()  # To match typical latitude/longitude plotting
    
    # Save the figure directly to a file
    fig.savefig(output_filename, format='png', bbox_inches='tight', pad_inches=0.1)
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
    parser.add_argument('--maxspeed', type=float, help='Exclude GPX tracks that exceed this speed (km/h).')
    
    args = parser.parse_args()
    
    if args.autoscale:
        resolution = autoscale_resolution_from_bbox(args.bbox, args.autoscale)
    elif args.resolution:
        resolution = tuple(args.resolution)
    
    plot_gpx_to_image(args.folder_path, args.output, resolution, args.bbox, args.maxspeed)
