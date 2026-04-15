let allData = [];

d3.csv("../data/data_final.csv").then(data => {
    data.forEach(d => {
        d.views = +d.views;
        d.likes = +d.likes;
        d.comment_count = +d.comment_count;
        d.publish_hour = +d.publish_hour;
        d.days_to_trending = +d.days_to_trending;
    });

    allData = data;

    populateCategories();

    console.log("Data loaded:", allData.length);

    // TEST ALL AGGREGATIONS
    testAggregations();
});


// =========================
// FILTERS
// =========================

function getByCountry(country) {
    return allData.filter(d => d.country === country);
}

function getByCategory(category) {
    return allData.filter(d => d.category_name === category);
}

function getByCountryAndCategory(country, category) {
    return allData.filter(d =>
        d.country === country && d.category_name === category
    );
}


// =========================
// AGGREGATIONS
// =========================

function countByDay(data) {
    const counts = {};
    data.forEach(d => {
        counts[d.publish_day] = (counts[d.publish_day] || 0) + 1;
    });
    return counts;
}

function countByHour(data) {
    const counts = {};
    data.forEach(d => {
        counts[d.publish_hour] = (counts[d.publish_hour] || 0) + 1;
    });
    return counts;
}

function avgDaysToTrending(data) {
    return d3.mean(data, d => d.days_to_trending);
}

function countByCategory(data) {
    const counts = {};
    data.forEach(d => {
        counts[d.category_name] = (counts[d.category_name] || 0) + 1;
    });
    return counts;
}

function getAverageStats(data) {
    return {
        avgViews: d3.mean(data, d => d.views),
        avgLikes: d3.mean(data, d => d.likes),
        avgDays: d3.mean(data, d => d.days_to_trending)
    };
}


// =========================
// UI
// =========================

function populateCategories() {
    const select = document.getElementById("categorySelect");

    const categories = [...new Set(allData.map(d => d.category_name))].sort();

    categories.forEach(cat => {
        const option = document.createElement("option");
        option.value = cat;
        option.textContent = cat;
        select.appendChild(option);
    });
}

function runQuery() {
    const country = document.getElementById("countrySelect").value;
    const category = document.getElementById("categorySelect").value;

    let results;

    if (category) {
        results = getByCountryAndCategory(country, category);
    } else {
        results = getByCountry(country);
    }

    displayResults(results);
    displayStats(results);
}


// =========================
// DISPLAY
// =========================

function displayResults(data) {
    const container = document.getElementById("results");
    container.innerHTML = "";

    const sample = data.slice(0, 20);

    sample.forEach(d => {
        const div = document.createElement("div");
        div.className = "video";

        div.innerHTML = `
            <img src="${d.thumbnail_link}" />
            <div>
                <strong>${d.title}</strong><br>
                ${d.category_name} | ${d.views} views
            </div>
        `;

        container.appendChild(div);
    });
}

function displayStats(data) {
    const statsDiv = document.getElementById("stats");

    const avg = getAverageStats(data);
    const avgDays = avgDaysToTrending(data);
    const dayCounts = countByDay(data);
    const hourCounts = countByHour(data);

    statsDiv.innerHTML = `
        <p><strong>Average Views:</strong> ${Math.round(avg.avgViews)}</p>
        <p><strong>Average Likes:</strong> ${Math.round(avg.avgLikes)}</p>
        <p><strong>Average Days to Trending:</strong> ${avgDays.toFixed(2)}</p>
        <p><strong>Videos per Day:</strong> ${JSON.stringify(dayCounts)}</p>
        <p><strong>Videos per Hour:</strong> ${JSON.stringify(hourCounts)}</p>
    `;
}


// =========================
// TEST FUNCTION
// =========================

function testAggregations() {
    const sample = getByCountry("FR");

    console.log("TEST Aggregations:");

    console.log("Count by day:", countByDay(sample));
    console.log("Count by hour:", countByHour(sample));
    console.log("Avg days:", avgDaysToTrending(sample));
    console.log("Category counts:", countByCategory(sample));
    console.log("Average stats:", getAverageStats(sample));
}
