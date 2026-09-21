function goToRules() {
    const sound = new Audio("/static/assets/prom-whoosh.mp3");

    sound.volume = 0.8;
    sound.play();

    document.body.classList.add("page-exit");

    setTimeout(() => {
        window.location.href = "/rules";
    }, 500);
}

function goToDetails() {
    document.body.classList.add("page-exit");

    setTimeout(() => {
        window.location.href = "/details";
    }, 500);
}

// Fix blank page when using the browser Back/Forward buttons
window.addEventListener("pageshow", () => {
    document.body.classList.remove("page-exit");
});