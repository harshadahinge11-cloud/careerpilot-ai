
const API_URL = "";

const loginForm = document.getElementById("loginForm");
const registerForm = document.getElementById("registerForm");
const message = document.getElementById("authMessage");


/* =========================
   MESSAGE FUNCTION
========================= */

function showMessage(text, type) {

    if (message) {

        message.textContent = text;
        message.className = "auth-message " + type;

    }

}


/* =========================
   REGISTER
========================= */

if (registerForm) {

    registerForm.addEventListener("submit", async (e) => {

        e.preventDefault();

        const name =
            document.getElementById("name").value.trim();

        const email =
            document.getElementById("email").value.trim().toLowerCase();

        const password =
            document.getElementById("password").value;

        const confirm =
            document.getElementById("confirmPassword").value;


        /* =========================
           VALIDATION
        ========================= */

        if (!name) {

            showMessage(
                "Please enter your name.",
                "error"
            );

            return;
        }


        if (!email) {

            showMessage(
                "Please enter your email address.",
                "error"
            );

            return;
        }


        if (password.length < 6) {

            showMessage(
                "Password must contain at least 6 characters.",
                "error"
            );

            return;
        }


        if (password !== confirm) {

            showMessage(
                "Passwords do not match.",
                "error"
            );

            return;
        }


        /* =========================
           REGISTER DATA
        ========================= */

        const user = {

            name: name,
            email: email,
            password: password

        };


        try {

            showMessage(
                "Creating your account...",
                "success"
            );


            const response = await fetch(
                `${API_URL}/auth/register`,
                {
                    method: "POST",

                    headers: {
                        "Content-Type": "application/json"
                    },

                    body: JSON.stringify(user)
                }
            );


            const data = await response.json();


            /* =========================
               REGISTER ERROR
            ========================= */

            if (!response.ok) {

                showMessage(
                    data.detail || "Registration failed.",
                    "error"
                );

                return;
            }


            /* =========================
               REGISTER SUCCESS
            ========================= */

            showMessage(
                "Account created successfully. Redirecting to login...",
                "success"
            );


            setTimeout(() => {

                window.location.href = "login.html";

            }, 1000);


        } catch (error) {

            console.error(
                "Registration error:",
                error
            );


            showMessage(
                "Cannot connect to the backend. Please start FastAPI.",
                "error"
            );

        }

    });

}


/* =========================
   LOGIN
========================= */

if (loginForm) {

    loginForm.addEventListener("submit", async (e) => {

        e.preventDefault();


        const email =
            document.getElementById("email").value.trim().toLowerCase();

        const password =
            document.getElementById("password").value;


        /* =========================
           VALIDATION
        ========================= */

        if (!email) {

            showMessage(
                "Please enter your email address.",
                "error"
            );

            return;
        }


        if (!password) {

            showMessage(
                "Please enter your password.",
                "error"
            );

            return;
        }


        const loginData = {

            email: email,
            password: password

        };


        try {

            showMessage(
                "Signing you in...",
                "success"
            );


            const response = await fetch(
                `${API_URL}/auth/login`,
                {
                    method: "POST",

                    headers: {
                        "Content-Type": "application/json"
                    },

                    body: JSON.stringify(loginData)
                }
            );


            const data = await response.json();


            /* =========================
               LOGIN ERROR
            ========================= */

            if (!response.ok) {

                showMessage(
                    data.detail ||
                    "Email or password is incorrect.",
                    "error"
                );

                return;
            }


            /* =========================
               SAVE LOGIN INFORMATION
            ========================= */

            localStorage.setItem(
                "careerpilot_logged_in",
                "true"
            );


            localStorage.setItem(
                "careerpilot_user_id",
                data.user_id
            );


            localStorage.setItem(
                "careerpilot_name",
                data.name
            );


            localStorage.setItem(
                "careerpilot_email",
                data.email || email
            );


            /* =========================
               LOGIN SUCCESS
            ========================= */

            showMessage(
                "Sign in successful. Opening your workspace...",
                "success"
            );


            setTimeout(() => {

                window.location.href =
                    "dashboard.html";

            }, 700);


        } catch (error) {

            console.error(
                "Login error:",
                error
            );


            showMessage(
                "Cannot connect to the backend. Please start FastAPI.",
                "error"
            );

        }

    });

}