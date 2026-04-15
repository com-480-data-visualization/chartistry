# Running the queries

This is a simple prototype to test the data queries and filtering on the dataset.

## Project Structure

Make sure your folders are organized like this:

```
chartistry/
│── data/
│     └── data_final.csv
│
│── garik_draft/
│     ├── index.html
│     └── queries.js
```

## How to Run

1. Go to the project root:

```
cd chartistry
```

2. Start a local server:

```
python -m http.server 8000
```

3. Open in browser:

```
http://localhost:8000/garik_draft
```

## How to Use

- Select a country
- Select a category
- Click Search

You will see:
- a list of videos
- basic statistics

## Purpose

- Test data filtering
- Validate queries
- Prepare for visualizations
