from flask import Flask, request
import psycopg2

app = Flask(__name__)

def get_connection():
    return psycopg2.connect(
        host="localhost",
        port=5432,
        dbname="postgres",
        user="postgres",
        password="your_postgres_passwords"
    )

@app.route("/", methods=["GET"])
def home():
    return """
    <html>
    <head>
        <title>Airline Search</title>
        <style>
            body {
                font-family: Arial, sans-serif;
                background-color: #f4f6f8;
                margin: 0;
                padding: 0;
            }
            .container {
                max-width: 700px;
                margin: 60px auto;
                background: white;
                padding: 30px;
                border-radius: 12px;
                box-shadow: 0 4px 14px rgba(0, 0, 0, 0.08);
            }
            h1 {
                margin-top: 0;
                text-align: center;
            }
            label {
                font-weight: bold;
            }
            input, button {
                width: 100%;
                padding: 10px;
                margin-top: 6px;
                margin-bottom: 18px;
                box-sizing: border-box;
            }
            button {
                background-color: #1f6feb;
                color: white;
                border: none;
                border-radius: 8px;
                cursor: pointer;
                font-size: 16px;
            }
            button:hover {
                background-color: #1558b0;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>Search Flights</h1>
            <form action="/search" method="get">
                <label>Source airport code:</label>
                <input type="text" name="source" required>

                <label>Destination airport code:</label>
                <input type="text" name="destination" required>

                <label>Start date:</label>
                <input type="date" name="start_date" required>

                <label>End date:</label>
                <input type="date" name="end_date" required>

                <button type="submit">Search</button>
            </form>
        </div>
    </body>
    </html>
    """

@app.route("/search", methods=["GET"])
def search():
    source = request.args.get("source", "").strip().upper()
    destination = request.args.get("destination", "").strip().upper()
    start_date = request.args.get("start_date", "")
    end_date = request.args.get("end_date", "")

    try:
        conn = get_connection()
        cur = conn.cursor()

        query = """
            SELECT
                f.flight_number,
                f.departure_date,
                fs.origin_code,
                fs.dest_code,
                fs.departure_time
            FROM Flight f
            JOIN FlightService fs
              ON f.flight_number = fs.flight_number
            WHERE fs.origin_code = %s
              AND fs.dest_code = %s
              AND f.departure_date BETWEEN %s AND %s
            ORDER BY f.departure_date, f.flight_number;
        """

        cur.execute(query, (source, destination, start_date, end_date))
        rows = cur.fetchall()

        cur.close()
        conn.close()

        html = f"""
        <html>
        <head>
            <title>Flight Results</title>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    background-color: #f4f6f8;
                    margin: 0;
                    padding: 0;
                }}
                .container {{
                    max-width: 950px;
                    margin: 60px auto;
                    background: white;
                    padding: 30px;
                    border-radius: 12px;
                    box-shadow: 0 4px 14px rgba(0, 0, 0, 0.08);
                }}
                h1 {{
                    margin-top: 0;
                    text-align: center;
                }}
                .summary {{
                    margin-bottom: 20px;
                    line-height: 1.8;
                }}
                table {{
                    width: 100%;
                    border-collapse: collapse;
                    margin-top: 20px;
                }}
                th, td {{
                    border: 1px solid #ddd;
                    padding: 12px;
                    text-align: left;
                }}
                th {{
                    background-color: #f0f4f8;
                }}
                a {{
                    color: #1f6feb;
                    text-decoration: none;
                }}
                a:hover {{
                    text-decoration: underline;
                }}
                .back-link {{
                    display: inline-block;
                    margin-top: 20px;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>Available Flights</h1>
                <div class="summary">
                    <p><b>Source:</b> {source}</p>
                    <p><b>Destination:</b> {destination}</p>
                    <p><b>Date range:</b> {start_date} to {end_date}</p>
                </div>
        """

        if rows:
            html += """
                <table>
                    <tr>
                        <th>Flight Number</th>
                        <th>Departure Date</th>
                        <th>Origin</th>
                        <th>Destination</th>
                        <th>Departure Time</th>
                    </tr>
            """
            for row in rows:
                flight_number, departure_date, origin_code, dest_code, departure_time = row
                html += f"""
                    <tr>
                        <td>
                            <a href="/flight_details?flight_number={flight_number}&departure_date={departure_date}">
                                {flight_number}
                            </a>
                        </td>
                        <td>{departure_date}</td>
                        <td>{origin_code}</td>
                        <td>{dest_code}</td>
                        <td>{departure_time}</td>
                    </tr>
                """
            html += "</table>"
        else:
            html += "<p>No flights found for that search.</p>"

        html += """
                <a class="back-link" href="/">Back</a>
            </div>
        </body>
        </html>
        """
        return html

    except Exception as e:
        return f"<h1>Error</h1><p>{e}</p><p><a href='/'>Back</a></p>"
    
@app.route("/flight_details", methods=["GET"])
def flight_details():
    flight_number = request.args.get("flight_number", "")
    departure_date = request.args.get("departure_date", "")

    try:
        conn = get_connection()
        cur = conn.cursor()

        query = """
            SELECT
                f.flight_number,
                f.departure_date,
                a.capacity,
                COUNT(b.pid) AS booked_seats,
                a.capacity - COUNT(b.pid) AS available_seats
            FROM Flight f
            JOIN Aircraft a
              ON f.plane_type = a.plane_type
            LEFT JOIN Booking b
              ON f.flight_number = b.flight_number
             AND f.departure_date = b.departure_date
            WHERE f.flight_number = %s
              AND f.departure_date = %s
            GROUP BY f.flight_number, f.departure_date, a.capacity;
        """

        cur.execute(query, (flight_number, departure_date))
        row = cur.fetchone()

        cur.close()
        conn.close()

        if row is None:
            return """
            <html>
            <head>
                <title>Flight Not Found</title>
                <style>
                    body {
                        font-family: Arial, sans-serif;
                        background-color: #f4f6f8;
                        margin: 0;
                        padding: 0;
                    }
                    .container {
                        max-width: 700px;
                        margin: 60px auto;
                        background: white;
                        padding: 30px;
                        border-radius: 12px;
                        box-shadow: 0 4px 14px rgba(0, 0, 0, 0.08);
                        text-align: center;
                    }
                    a {
                        color: #1f6feb;
                        text-decoration: none;
                    }
                </style>
            </head>
            <body>
                <div class="container">
                    <h1>Flight Not Found</h1>
                    <p>No details found for that flight.</p>
                    <p><a href="/">Back</a></p>
                </div>
            </body>
            </html>
            """

        flight_number, departure_date, capacity, booked_seats, available_seats = row

        return f"""
        <html>
        <head>
            <title>Flight Details</title>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    background-color: #f4f6f8;
                    margin: 0;
                    padding: 0;
                }}
                .container {{
                    max-width: 700px;
                    margin: 60px auto;
                    background: white;
                    padding: 30px;
                    border-radius: 12px;
                    box-shadow: 0 4px 14px rgba(0, 0, 0, 0.08);
                }}
                h1 {{
                    margin-top: 0;
                    text-align: center;
                }}
                .detail {{
                    font-size: 18px;
                    line-height: 1.9;
                }}
                a {{
                    color: #1f6feb;
                    text-decoration: none;
                }}
                a:hover {{
                    text-decoration: underline;
                }}
                .back-link {{
                    display: inline-block;
                    margin-top: 20px;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>Flight Details</h1>
                <div class="detail">
                    <p><b>Flight Number:</b> {flight_number}</p>
                    <p><b>Departure Date:</b> {departure_date}</p>
                    <p><b>Plane Capacity:</b> {capacity}</p>
                    <p><b>Booked Seats:</b> {booked_seats}</p>
                    <p><b>Available Seats:</b> {available_seats}</p>
                </div>
                <a class="back-link" href="/">Back to Search</a>
            </div>
        </body>
        </html>
        """

    except Exception as e:
        return f"<h1>Error</h1><p>{e}</p><p><a href='/'>Back</a></p>"
    

if __name__ == "__main__":
    app.run(debug=True)