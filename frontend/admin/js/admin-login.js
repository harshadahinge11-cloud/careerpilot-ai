const API="";
const form=document.getElementById("adminLoginForm");
const message=document.getElementById("adminMessage");

document.getElementById("togglePassword").onclick=()=>{
  const p=document.getElementById("password");
  p.type=p.type==="password"?"text":"password";
  document.getElementById("togglePassword").textContent=p.type==="password"?"Show":"Hide";
};

function show(text,type=""){message.textContent=text;message.className="message "+type;}

form.addEventListener("submit",async e=>{
  e.preventDefault();
  show("Signing in...");
  const email=document.getElementById("email").value.trim().toLowerCase();
  const password=document.getElementById("password").value;
  try{
    const res=await fetch(API+"/admin/login",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({email,password})});
    const data=await res.json();
    if(!res.ok) throw new Error(data.detail||"Admin login failed.");
     localStorage.setItem("careerpilot_admin_key", data.admin_key);
     localStorage.setItem("careerpilot_admin_name", data.name || "Admin");
    show("Admin login successful. Opening console...","success");
    setTimeout(()=>location.href="dashboard.html",500);
  }catch(err){show(err.message,"error");}
});