document.querySelectorAll(".view-btn").forEach(button => {

    button.addEventListener("click", function(e){

        e.preventDefault();
        e.stopPropagation();

        // Open CV
        window.open("<cvURL>", "_blank");

    });

});

document.querySelectorAll(".download-btn").forEach(button => {

    button.addEventListener("click", function(e){

        e.preventDefault();
        e.stopPropagation();

        // Download CV
        window.location.href = "<cvDownloadURL>";

    });

});


const search = document.getElementById("search");

search.addEventListener("keyup", function () {

    const value = this.value.toLowerCase();

    document.querySelectorAll(".intern-card").forEach(card => {

        const text = card.textContent.toLowerCase();

        card.style.display = text.includes(value) ? "" : "none";

    });

});