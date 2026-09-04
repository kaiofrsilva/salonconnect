// ==========================
// MENU MOBILE
// ==========================
function toggleMenu() {
    const menu = document.getElementById("menu");

    if (menu) {
        menu.classList.toggle("show");
    }
}


// ==========================
// LOGIN
// ==========================
async function logar() {

    const email = document.getElementById("email").value.trim();
    const senha = document.getElementById("senha").value.trim();

    try {

        const resposta = await fetch("/login", {

            method: "POST",

            headers: {
                "Content-Type": "application/json"
            },

            body: JSON.stringify({
                email,
                senha
            })

        });

        const dados = await resposta.json();

if (dados.sucesso) {

    if (dados.nome) {
        localStorage.setItem("logado", JSON.stringify({
            nome: dados.nome
        }));
    }

    window.location.href = dados.redirect;

} else {

    alert(dados.mensagem);

}

    } catch (erro) {

        console.error(erro);

        alert("Erro ao realizar login.");

    }

}


// ==========================
// MOSTRAR USUÁRIO
// ==========================
function verificarLogin() {

    const user = JSON.parse(localStorage.getItem("logado"));

    const loginBtn = document.querySelector(".btn-login");

    const userArea = document.getElementById("userArea");

    if (!loginBtn || !userArea)
        return;

    if (user) {

        loginBtn.style.display = "none";

        userArea.innerHTML = `

            <div class="usuario-logado">

                <span style="color:#fff;font-weight:500">

                    👋 Olá,
                    <strong style="color:#7CFFB1">${user.nome}</strong>

                </span>

                <button class="btn-sair" onclick="sair()">

                    Sair

                </button>

            </div>

        `;

    } else {

        loginBtn.style.display = "flex";

        userArea.innerHTML = "";

    }

}


// ==========================
// LOGOUT
// ==========================
function sair() {

    localStorage.removeItem("logado");

    window.location.href = "/";

}


// ==========================
// LOGIN BOX
// ==========================
function toggleLogin() {

    const box = document.getElementById("loginBox");

    if (!box)
        return;

    box.style.display =
        box.style.display === "block"
        ? "none"
        : "block";

}


// ==========================
// FECHAR LOGIN
// ==========================
document.addEventListener("click", function (e) {

    const box = document.getElementById("loginBox");

    const btn = document.querySelector(".btn-login");

    if (!box || !btn)
        return;

    if (!box.contains(e.target) && !btn.contains(e.target)) {

        box.style.display = "none";

    }

});


// ==========================
// PROTEGER PÁGINAS
// ==========================
function protegerPagina() {

    const user = JSON.parse(localStorage.getItem("logado"));

    if (!user) {

        window.location.href = "/";

    }

}


// ==========================
// INICIALIZAÇÃO
// ==========================
document.addEventListener("DOMContentLoaded", function () {

    verificarLogin();

});


// ==========================
// MENU ATIVO
// ==========================
const links = document.querySelectorAll(".menu a");

links.forEach(link => {

    link.addEventListener("click", function () {

        links.forEach(l => l.classList.remove("active"));

        this.classList.add("active");

    });

});


window.addEventListener("scroll", () => {

    const sections = document.querySelectorAll("section");

    let scrollPos = window.scrollY + 150;

    sections.forEach(section => {

        if (

            scrollPos >= section.offsetTop &&

            scrollPos < section.offsetTop + section.offsetHeight

        ) {

            links.forEach(link => {

                link.classList.remove("active");

                if (link.getAttribute("href") === "#" + section.id) {

                    link.classList.add("active");

                }

            });

        }

    });

});