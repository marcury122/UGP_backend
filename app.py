# create an enviornment then start flash file
#  creating an enviornment:  python3 -m venv venv
# activate the enviornment: source venv/bin/activate
# start the server: python3 app.py
from flask import Flask, request, jsonify
from flask_cors import CORS
import json
import random
import numpy as np

app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": "http://localhost:3000"}})

def calculate_adjusted_usage(data, selected_days, selected_set, selected_month, is_generated=False):
    try:
        avg_usg = data["algoData"]["avgUsg"]
        data_days = data["dataDays"]
        interval_length = data["intervalLength"]
        percentage_ranges = data["algoData"]["data"].get(selected_set)

        if percentage_ranges is None:
            raise ValueError(f"Invalid selected_set: {selected_set}")

        def get_random_percentage(range_tuple):
            return random.uniform(range_tuple[0], range_tuple[1]) if isinstance(range_tuple, list) and len(range_tuple) == 2 else None

        cumulative_total = 0
        result = []

        for day in selected_days:
            if day < 1 or day > data_days:
                raise ValueError(f"Invalid day: {day}")

            usage_per_day = avg_usg / data_days
            number_reads = 24 * 3600 / interval_length
            usage_per_interval = usage_per_day / number_reads
            y = []

            for time_range, percentage_range in percentage_ranges.items():
                if time_range == "months":
                    continue

                random_percentage = get_random_percentage(percentage_range)
                adjusted_interval_usage = usage_per_interval * (random_percentage / 100)
                y.append(adjusted_interval_usage / 2)

            result.append(y)
            daily_adjusted_usage = sum(y)
            cumulative_total += daily_adjusted_usage

        return result, cumulative_total

    except Exception as e:
        print(f"Error in calculate_adjusted_usage: {str(e)}")
        raise

@app.route('/api/data', methods=['POST'])
def get_data():
    try:
        content = request.json
        selected_set = content['selected_set']
        selected_month = content['selected_month']
        selected_days = [int(day) for day in content['selected_days']]
        c_rate = content.get('c_rate', 0.5) # Default c_rate to 0.5 if not provided

        with open("UG.JSON", "r") as file:
            input_data = json.load(file)
        with open("UG-2.JSON", "r") as f:
            input1 = json.load(f)

        consumption, total_consumption = calculate_adjusted_usage(input_data, selected_days, selected_set, selected_month, is_generated=False)
        generation, total_generation = calculate_adjusted_usage(input1, selected_days, selected_set, selected_month, is_generated=True)

        time_steps = 12
        max_bh = 5
        x = c_rate * 2
        max_change = max_bh * x
        battery_data = []
        grid_data = []
        soc_data = []  # List to store SOC data for each day

        for day_index in range(len(selected_days)):
            generation_flat = generation[day_index]
            consumption_flat = consumption[day_index]
            battery = [0] * time_steps
            grid = [0] * time_steps
            soc = [0] * time_steps  # State of Charge data
            bh = 0  # Battery energy level

            for i in range(time_steps):
                bh += generation_flat[i] - consumption_flat[i]
                if bh < 0:
                    grid[i] = -bh
                    bh = 0
                elif bh > max_bh:
                    grid[i] = max_bh - bh
                    bh = max_bh
                else:
                    grid[i] = 0

                battery[i] = consumption_flat[i] - generation_flat[i] - grid[i]
                soc[i] = (bh / max_bh) * 100  # Calculate SOC as a percentage

            battery_data.append(battery)
            grid_data.append(grid)
            soc_data.append(soc)  # Add the SOC data for the day

        return jsonify({
            'consumption': consumption,
            'generation': generation,
            'battery': battery_data,
            'grid': grid_data,
            'soc': soc_data  # Return the SOC data in the response
        })
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000, debug=True)
