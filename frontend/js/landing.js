document.addEventListener("DOMContentLoaded", () => {

    /* =========================================================
       CAREERPILOT AI
       PREMIUM LANDING PAGE ANIMATION ENGINE
    ========================================================= */

    if (typeof gsap === "undefined") {
        console.error("GSAP is not loaded.");
        return;
    }


    /* =========================================================
       GLOBAL SETTINGS
    ========================================================= */

    const visual = document.querySelector(".hero-visual");
    const person = document.querySelector(".person");

    if (!visual) return;


    /* =========================================================
       1. CINEMATIC PAGE ENTRANCE
    ========================================================= */

    const intro = gsap.timeline({
        defaults: {
            ease: "power3.out"
        }
    });

    intro

        .from(".navbar", {
            y: -35,
            opacity: 0,
            duration: 0.9
        })

        .from(".eyebrow", {
            y: 25,
            opacity: 0,
            duration: 0.6
        }, "-=0.4")

        .from(".hero h1", {
            y: 55,
            opacity: 0,
            duration: 1
        }, "-=0.3")

        .from(".hero-left > p", {
            y: 25,
            opacity: 0,
            duration: 0.7
        }, "-=0.5")

        .from(".hero-actions", {
            y: 25,
            opacity: 0,
            duration: 0.6
        }, "-=0.4")

        .from(".checks span", {
            y: 15,
            opacity: 0,
            stagger: 0.08,
            duration: 0.4
        }, "-=0.3")

        .from(".hero-visual", {
            scale: 0.9,
            opacity: 0,
            duration: 1.2
        }, "-=0.5");


    /* =========================================================
       2. PERSON ENTRANCE
    ========================================================= */

    gsap.from(person, {
        y: 90,
        scale: 0.88,
        opacity: 0,
        duration: 1.5,
        delay: 0.7,
        ease: "power4.out"
    });


    /* =========================================================
       3. PERSON IDLE MOVEMENT
    ========================================================= */

    gsap.to(person, {
        y: -6,
        duration: 3.2,
        repeat: -1,
        yoyo: true,
        ease: "sine.inOut"
    });


    /* =========================================================
       4. BACKGROUND GLOW
    ========================================================= */

    gsap.to(".visual-glow", {
        scale: 1.2,
        opacity: 0.7,
        duration: 4,
        repeat: -1,
        yoyo: true,
        ease: "sine.inOut"
    });


    /* =========================================================
       5. ORBIT RINGS
    ========================================================= */

    gsap.to(".orbit-one", {
        rotation: 360,
        duration: 32,
        repeat: -1,
        ease: "none"
    });

    gsap.to(".orbit-two", {
        rotation: -360,
        duration: 45,
        repeat: -1,
        ease: "none"
    });


    /* =========================================================
       6. CAREER CARD ORBIT
    ========================================================= */

    const cards = [

        {
            selector: ".python-card",
            angle: 215,
            rx: 245,
            ry: 170,
            duration: 30
        },

        {
            selector: ".sql-card",
            angle: 330,
            rx: 245,
            ry: 170,
            duration: 32
        },

        {
            selector: ".ml-card",
            angle: 145,
            rx: 270,
            ry: 190,
            duration: 34
        },

        {
            selector: ".resume-card",
            angle: 35,
            rx: 285,
            ry: 180,
            duration: 36
        },

        {
            selector: ".ai-card",
            angle: 255,
            rx: 280,
            ry: 195,
            duration: 33
        },

        {
            selector: ".career-card",
            angle: 75,
            rx: 275,
            ry: 195,
            duration: 35
        }
    ];


    cards.forEach((card, index) => {

        const element =
            document.querySelector(card.selector);

        if (!element) return;


        const state = {
            angle: card.angle
        };


        let paused = false;


        /* Center cards */

        gsap.set(element, {
            left: "50%",
            top: "50%",
            xPercent: -50,
            yPercent: -50
        });


        /* Card entrance */

        gsap.from(element, {
            scale: 0.5,
            opacity: 0,
            duration: 1,
            delay: 1.1 + index * 0.12,
            ease: "back.out(1.6)"
        });


        /* Main orbit */

        const orbitTween = gsap.to(state, {

            angle: card.angle + 360,

            duration: card.duration,

            repeat: -1,

            ease: "none",

            onUpdate: () => {

                const radians =
                    state.angle * Math.PI / 180;


                const x =
                    Math.cos(radians) * card.rx;


                const y =
                    Math.sin(radians) * card.ry;


                const depth =
                    (Math.sin(radians) + 1) / 2;


                /*
                   Front cards:
                   brighter and slightly larger.
                */

                const opacity =
                    0.65 + depth * 0.35;


                const rotation =
                    Math.cos(radians) * 4;


                gsap.set(element, {

                    x: x,

                    y: y,

                    rotation: rotation,

                    opacity: opacity

                });


                /*
                   Real depth layering.
                */

                element.style.zIndex =
                    depth < 0.45 ? "5" : "30";

            }

        });


        /* =====================================================
           CARD HOVER
        ===================================================== */

        element.addEventListener("mouseenter", () => {

            paused = true;

            orbitTween.timeScale(0.15);

            gsap.to(element, {

                scale: 1.08,

                opacity: 1,

                duration: 0.35,

                ease: "power3.out"

            });

        });


        element.addEventListener("mouseleave", () => {

            paused = false;

            orbitTween.timeScale(1);

            gsap.to(element, {

                scale: 1,

                duration: 0.4,

                ease: "power3.out"

            });

        });

    });


    /* =========================================================
       7. SKILL PILLS ORBIT
    ========================================================= */

    const pills = [

        {
            selector: ".pill-python",
            angle: 0,
            rx: 235,
            ry: 240,
            duration: 24
        },

        {
            selector: ".pill-sql",
            angle: 120,
            rx: 255,
            ry: 230,
            duration: 27
        },

        {
            selector: ".pill-aws",
            angle: 240,
            rx: 250,
            ry: 240,
            duration: 26
        }

    ];


    pills.forEach(pill => {

        const element =
            document.querySelector(pill.selector);

        if (!element) return;


        const state = {
            angle: pill.angle
        };


        gsap.set(element, {
            left: "50%",
            top: "50%",
            xPercent: -50,
            yPercent: -50
        });


        gsap.to(state, {

            angle: pill.angle + 360,

            duration: pill.duration,

            repeat: -1,

            ease: "none",

            onUpdate: () => {

                const radians =
                    state.angle * Math.PI / 180;


                gsap.set(element, {

                    x:
                        Math.cos(radians) *
                        pill.rx,

                    y:
                        Math.sin(radians) *
                        pill.ry,

                    rotation:
                        Math.cos(radians) * 5

                });

            }

        });

    });


    /* =========================================================
       8. AI SCANNING CARD
    ========================================================= */

    const scanner =
        document.querySelector(".scanning-card");

    if (scanner) {

        gsap.from(scanner, {
            scale: 0.5,
            opacity: 0,
            duration: 0.8,
            delay: 1.8,
            ease: "back.out(1.7)"
        });


        gsap.to(scanner, {

            y: -7,

            duration: 2.3,

            repeat: -1,

            yoyo: true,

            ease: "sine.inOut"

        });

    }


    /* =========================================================
       9. PULSE EFFECT
    ========================================================= */

    gsap.to(".pulse", {

        scale: 2.2,

        opacity: 0.25,

        duration: 1.1,

        repeat: -1,

        yoyo: true,

        ease: "sine.inOut"

    });


    /* =========================================================
       10. RESUME PROGRESS
    ========================================================= */

    const resumeBar =
        document.querySelector(".resume-bar i");

    if (resumeBar) {

        gsap.fromTo(

            resumeBar,

            {
                width: "0%"
            },

            {
                width: "87%",
                duration: 2,
                delay: 1.8,
                ease: "power3.out"
            }

        );

    }


    /* =========================================================
       11. DYNAMIC AI PARTICLES
    ========================================================= */

    function createParticle() {

        const particle =
            document.createElement("span");

        particle.style.position = "absolute";

        particle.style.width =
            Math.random() * 3 + 1 + "px";

        particle.style.height =
            particle.style.width;

        particle.style.borderRadius = "50%";

        particle.style.background =
            "rgba(135,120,255," +
            (Math.random() * 0.45 + 0.2) +
            ")";

        particle.style.boxShadow =
            "0 0 10px rgba(120,100,255,.7)";

        particle.style.left =
            Math.random() * 100 + "%";

        particle.style.top =
            Math.random() * 100 + "%";

        particle.style.pointerEvents = "none";

        particle.style.zIndex = "1";

        visual.appendChild(particle);


        gsap.to(particle, {

            x:
                Math.random() * 100 - 50,

            y:
                Math.random() * 120 - 60,

            opacity: 0,

            duration:
                Math.random() * 4 + 3,

            repeat: -1,

            delay:
                Math.random() * 3,

            ease: "sine.inOut"

        });

    }


    for (let i = 0; i < 28; i++) {

        createParticle();

    }


    /* =========================================================
       12. ENERGY DOTS AROUND PERSON
    ========================================================= */

    function createEnergyDot(angle, speed) {

        const dot =
            document.createElement("span");

        dot.style.position = "absolute";

        dot.style.left = "50%";

        dot.style.top = "50%";

        dot.style.width = "5px";

        dot.style.height = "5px";

        dot.style.borderRadius = "50%";

        dot.style.background = "#8b7cff";

        dot.style.boxShadow =
            "0 0 15px rgba(120,100,255,.9)";

        dot.style.zIndex = "8";

        visual.appendChild(dot);


        const state = {
            angle: angle
        };


        gsap.to(state, {

            angle: angle + 360,

            duration: speed,

            repeat: -1,

            ease: "none",

            onUpdate: () => {

                const radians =
                    state.angle * Math.PI / 180;


                gsap.set(dot, {

                    x:
                        Math.cos(radians) *
                        205,

                    y:
                        Math.sin(radians) *
                        270

                });

            }

        });

    }


    createEnergyDot(20, 9);
    createEnergyDot(140, 12);
    createEnergyDot(260, 10);


    /* =========================================================
       13. CARD GLOW ON HOVER
    ========================================================= */

    document.querySelectorAll(
        ".floating-card, .resume-card, .ai-card, .career-card"
    ).forEach(card => {

        card.addEventListener("mouseenter", () => {

            gsap.to(card, {

                boxShadow:
                    "0 25px 70px rgba(0,0,0,.5), 0 0 40px rgba(105,90,255,.35)",

                duration: 0.3

            });

        });


        card.addEventListener("mouseleave", () => {

            gsap.to(card, {

                boxShadow:
                    "0 20px 60px rgba(0,0,0,.35), 0 0 30px rgba(83,64,190,.08)",

                duration: 0.4

            });

        });

    });


    /* =========================================================
       14. MOUSE PARALLAX
    ========================================================= */

    if (window.innerWidth > 900) {

        window.addEventListener("mousemove", event => {

            const mouseX =
                event.clientX / window.innerWidth - 0.5;

            const mouseY =
                event.clientY / window.innerHeight - 0.5;


            gsap.to(".hero-visual", {

                x: mouseX * 15,

                y: mouseY * 10,

                duration: 1.3,

                ease: "power3.out"

            });


            gsap.to(".hero-left", {

                x: mouseX * -7,

                y: mouseY * -4,

                duration: 1.5,

                ease: "power3.out"

            });


            gsap.to(".orbit-one", {

                rotation:
                    mouseX * 8,

                duration: 1,

                ease: "power2.out"

            });

        });

    }


    /* =========================================================
       15. BUTTON MAGNETIC EFFECT
    ========================================================= */

    document.querySelectorAll(
        ".primary-btn, .nav-start"
    ).forEach(button => {

        button.addEventListener("mousemove", event => {

            const rect =
                button.getBoundingClientRect();


            const x =
                event.clientX -
                rect.left -
                rect.width / 2;


            const y =
                event.clientY -
                rect.top -
                rect.height / 2;


            gsap.to(button, {

                x: x * 0.12,

                y: y * 0.12,

                duration: 0.25,

                ease: "power2.out"

            });

        });


        button.addEventListener("mouseleave", () => {

            gsap.to(button, {

                x: 0,

                y: 0,

                duration: 0.5,

                ease: "elastic.out(1,.5)"

            });

        });

    });


    /* =========================================================
       16. STATS COUNTER
    ========================================================= */

    document.querySelectorAll(".stats b")
        .forEach(number => {

            const original =
                number.textContent.trim();


            const value =
                parseFloat(
                    original.replace(/[^0-9.]/g, "")
                );


            if (isNaN(value)) return;


            let suffix = "";

            if (original.includes("K")) {
                suffix = "K+";
            }

            if (original.includes("%")) {
                suffix = "%";
            }

            if (original.includes("×")) {
                suffix = "×";
            }


            const counter = {
                value: 0
            };


            gsap.to(counter, {

                value: value,

                duration: 2.2,

                delay: 1.5,

                ease: "power2.out",

                onUpdate: () => {

                    number.textContent =
                        Math.floor(counter.value) +
                        suffix;

                }

            });

        });


    /* =========================================================
       17. SCROLL REVEAL
    ========================================================= */

    const revealItems =
        document.querySelectorAll(
            ".stats, .content-section, .about, .cta"
        );


    const observer =
        new IntersectionObserver(

            entries => {

                entries.forEach(entry => {

                    if (!entry.isIntersecting) return;


                    gsap.fromTo(

                        entry.target,

                        {
                            y: 60,
                            opacity: 0
                        },

                        {
                            y: 0,
                            opacity: 1,
                            duration: 1,
                            ease: "power3.out"
                        }

                    );


                    observer.unobserve(
                        entry.target
                    );

                });

            },

            {
                threshold: 0.12
            }

        );


    revealItems.forEach(item => {

        observer.observe(item);

    });


    /* =========================================================
       18. FEATURE CARD INTERACTION
    ========================================================= */

    document.querySelectorAll(
        ".feature-grid article, .steps article"
    ).forEach(card => {

        card.addEventListener("mouseenter", () => {

            gsap.to(card, {

                y: -9,

                scale: 1.025,

                duration: 0.35,

                ease: "power3.out"

            });

        });


        card.addEventListener("mouseleave", () => {

            gsap.to(card, {

                y: 0,

                scale: 1,

                duration: 0.4,

                ease: "power3.out"

            });

        });

    });


    /* =========================================================
       19. AI ANALYSIS TEXT EFFECT
    ========================================================= */

    const aiLabel =
        document.querySelector(".ai-label");


    if (aiLabel) {

        gsap.to(aiLabel, {

            opacity: 0.45,

            duration: 1,

            repeat: -1,

            yoyo: true,

            ease: "sine.inOut"

        });

    }


    /* =========================================================
       20. NAVIGATION ACTIVE EFFECT
    ========================================================= */

    document.querySelectorAll(
        ".navbar nav a"
    ).forEach(link => {

        link.addEventListener("mouseenter", () => {

            gsap.to(link, {

                y: -2,

                duration: 0.2

            });

        });


        link.addEventListener("mouseleave", () => {

            gsap.to(link, {

                y: 0,

                duration: 0.25

            });

        });

    });


    /* =========================================================
       21. CTA BREATHING
    ========================================================= */

    gsap.to(".cta .primary-btn", {

        boxShadow:
            "0 0 35px rgba(100,80,255,.4)",

        duration: 2,

        repeat: -1,

        yoyo: true,

        ease: "sine.inOut"

    });


    /* =========================================================
       22. REDUCED MOTION
    ========================================================= */

    if (
        window.matchMedia(
            "(prefers-reduced-motion: reduce)"
        ).matches
    ) {

        gsap.globalTimeline.pause();

    }


    console.log(
        "CareerPilot AI premium animation system loaded."
    );

});