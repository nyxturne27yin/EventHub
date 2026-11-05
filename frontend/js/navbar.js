(() => {
    "use strict";

    function addLogoutNavigation() {
        const token = sessionStorage.getItem("access_token");

        if (!token) return;

        const navbar = document.querySelector(".navbar");
        if (!navbar) return;

        // Admin and organizer already have their own logout handlers.
        if (navbar.querySelector(
            "#logoutButton, #logoutBtn, [data-eh-logout]"
        )) {
            return;
        }

        const navigation = navbar.querySelector(".navbar-collapse");
        if (!navigation) return;

        // Avoid inserting the logout item more than once.
        if (navigation.querySelector(".eh-nav-logout")) return;

        const logoutButton = document.createElement("button");

        logoutButton.type = "button";
        logoutButton.className = "nav-link eh-nav-logout";
        logoutButton.textContent = "Log out";
        logoutButton.setAttribute("aria-label", "Log out of EventHub");
        logoutButton.dataset.ehLogout = "true";

        logoutButton.addEventListener("click", () => {
            sessionStorage.removeItem("access_token");
            window.location.href = "login.html";
        });

        // Support both <ul class="navbar-nav"> and <div class="navbar-nav">.
        const navList = navigation.querySelector(".navbar-nav");

        if (!navList) {
            navigation.appendChild(logoutButton);
            return;
        }

        if (navList.tagName.toLowerCase() === "ul") {
            const listItem = document.createElement("li");
            listItem.className = "nav-item";
            listItem.appendChild(logoutButton);
            navList.appendChild(listItem);
        } else {
            navList.appendChild(logoutButton);
        }
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", addLogoutNavigation);
    } else {
        addLogoutNavigation();
    }
})();
