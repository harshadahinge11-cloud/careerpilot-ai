const API_URL = "";

document.addEventListener("DOMContentLoaded", async () => {

    /* =========================================
       GET LOGGED-IN USER
    ========================================= */

    const userId = localStorage.getItem("careerpilot_user_id");

    if (!userId) {
        window.location.href = "login.html";
        return;
    }


    /* =========================================
       LOAD DASHBOARD DATA
    ========================================= */

    try {

        const response =
            await fetch(`${API_URL}/dashboard/${userId}`);

        if (!response.ok) {
            throw new Error("Unable to load dashboard data.");
        }

        const data = await response.json();

        console.log("Dashboard data:", data);


        /* =========================================
           USER INFORMATION
        ========================================= */

        if (data.user) {

            const fullName =
                data.user.name || "User";

            const firstName =
                fullName.split(" ")[0];

            const userName =
                document.getElementById("userName");

            const userFullName =
                document.getElementById("userFullName");

            const userAvatar =
                document.getElementById("userAvatar");

            if (userName) {
                userName.textContent = firstName;
            }

            if (userFullName) {
                userFullName.textContent = fullName;
            }

            if (userAvatar) {

                const initials =
                    fullName
                        .split(" ")
                        .map(word => word.charAt(0))
                        .join("")
                        .substring(0, 2)
                        .toUpperCase();

                userAvatar.textContent = initials;
            }
        }


        /* =========================================
           RESUME SCORE
        ========================================= */

        const resumeScore =
            data.resume?.score || 0;

        const resumeScoreElement =
            document.getElementById("resumeScore");

        if (resumeScoreElement) {

            resumeScoreElement.textContent =
                `${resumeScore}%`;
        }


        /* =========================================
           SKILL GAP COUNT
        ========================================= */

        const skillGapCount =
            data.skill_gap?.count || 0;

        const skillGapElement =
            document.getElementById("skillGapCount");

        if (skillGapElement) {

            skillGapElement.textContent =
                `${skillGapCount} skills found`;
        }


        /* =========================================
           JOB MATCH COUNT
        ========================================= */

        const jobMatchCount =
            data.jobs?.matches || 0;

        const jobMatchElement =
            document.getElementById("jobMatchCount");

        if (jobMatchElement) {

            jobMatchElement.textContent =
                `${jobMatchCount} matches`;
        }


        /* =========================================
           SKILLS
        ========================================= */

        const skills =
            data.skills?.list || [];

        const pythonScore =
            findSkillScore(skills, "python");

        const sqlScore =
            findSkillScore(skills, "sql");

        const cloudScore =
            findSkillScore(skills, "cloud");


        updateSkill(
            "pythonScore",
            "pythonBar",
            pythonScore
        );

        updateSkill(
            "sqlScore",
            "sqlBar",
            sqlScore
        );

        updateSkill(
            "cloudScore",
            "cloudBar",
            cloudScore
        );


        /* =========================================
           CAREER DIRECTION
        ========================================= */

        const careerDirection =
            document.getElementById("careerDirection");

        if (
            careerDirection &&
            data.career_report
        ) {

            const report =
                data.career_report;

            if (report.career_direction) {

                careerDirection.textContent =
                    report.career_direction;
            }
        }


        /* =========================================
           CAREER READINESS
        ========================================= */

        const readiness =
            calculateReadiness(
                resumeScore,
                skills.length,
                skillGapCount,
                jobMatchCount
            );

        const readinessElement =
            document.getElementById("readinessScore");

        if (readinessElement) {

            readinessElement.textContent =
                `${readiness}%`;
        }

        updateReadinessRing(readiness);


    } catch (error) {

        console.error(
            "Dashboard error:",
            error
        );

    }


    /* =========================================
       LOGOUT
    ========================================= */

    const logoutBtn =
        document.getElementById("logoutBtn");

    if (logoutBtn) {

        logoutBtn.addEventListener(
            "click",
            function (e) {

                e.preventDefault();

                localStorage.removeItem(
                    "careerpilot_logged_in"
                );

                localStorage.removeItem(
                    "careerpilot_user_id"
                );

                localStorage.removeItem(
                    "careerpilot_name"
                );

                localStorage.removeItem(
                    "careerpilot_email"
                );

                window.location.href =
                    "login.html";
            }
        );
    }

});


/* =========================================
   FIND SKILL SCORE
========================================= */

function findSkillScore(skills, skillName) {

    const skill =
        skills.find(item => {

            return String(
                item.skill_name || ""
            ).toLowerCase()
                .includes(skillName.toLowerCase());

        });

    if (!skill) {
        return 0;
    }

    return Number(
        skill.skill_score || 0
    );
}


/* =========================================
   UPDATE SKILL
========================================= */

function updateSkill(
    scoreId,
    barId,
    score
) {

    const scoreElement =
        document.getElementById(scoreId);

    if (scoreElement) {

        scoreElement.textContent =
            `${score}%`;
    }

    const bar =
        document.getElementById(barId);

    if (bar) {

        bar.style.width =
            `${score}%`;
    }
}


/* =========================================
   CAREER READINESS
========================================= */

function calculateReadiness(
    resumeScore,
    skillCount,
    skillGapCount,
    jobMatchCount
) {

    let score = resumeScore;

    if (skillCount > 0) {
        score += Math.min(
            skillCount * 2,
            10
        );
    }

    if (jobMatchCount > 0) {
        score += Math.min(
            jobMatchCount,
            10
        );
    }

    if (skillGapCount > 0) {
        score -= Math.min(
            skillGapCount * 2,
            10
        );
    }

    return Math.max(
        0,
        Math.min(100, Math.round(score))
    );
}


/* =========================================
   READINESS RING
========================================= */

function updateReadinessRing(score) {

    const ring =
        document.getElementById(
            "readinessRing"
        );

    if (!ring) {
        return;
    }

    ring.style.background = `
        radial-gradient(
            circle at center,
            #0b0e1b 57%,
            transparent 58%
        ),
        conic-gradient(
            #8b5cf6 0 ${score}%,
            rgba(255,255,255,.06) ${score}%
        )
    `;
}