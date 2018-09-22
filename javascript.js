window.onscroll = () => {
  const nav = document.querySelector('#navbar');
  if(this.scrollY >= 100) nav.className = 'navbar navbar-expand-md  navbar-dark bg-dark fixed-top'; else nav.className = 'navbar navbar-expand-md  navbar-dark bg-dark';
}



$("#homepage").on("click",function(){
        $('html,body').animate({
        scrollTop: $(".homepage").offset().top},
        'slow');
})
$("#aboutus").on("click",function(){
        $('html,body').animate({
        scrollTop: $("#section2").offset().top},
        'slow');
})
$("#services").on("click",function(){
        $('html,body').animate({
        scrollTop: $("#section3").offset().top},
        'slow');
})
$("#contact").on("click",function(){
        $('html,body').animate({
        scrollTop: $(".contactform").offset().top},
        'slow');
})
$(window).scroll(function() {
    if ($(this).scrollTop() > 50 ) {
        $('.scrolltop:hidden').stop(true, true).fadeIn();
    } else {
        $('.scrolltop').stop(true, true).fadeOut();
    }
});
$(function(){$(".scroll").click(function(){$("html,body").animate({scrollTop:$(".homepage").offset().top},"1000");return false})})



var text = ["<h1>Web Developer.</h1>","<h1>Programmer.</h1>","<h1> My Portfolio.</h1>"];
var counter = 0;
var elem = document.querySelector(".typewriter");
var inst = setInterval(change,4000);

function change() {
  elem.innerHTML = text[counter];
  counter++;
  if (counter >= text.length) {
    counter = 0;
    // clearInterval(inst); // uncomment this if you want to stop refreshing after one cycle
  }
}
