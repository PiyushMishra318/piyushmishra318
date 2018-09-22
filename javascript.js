window.onscroll = () => {
  const nav = document.querySelector('#navbar');
  if(this.scrollY >= 150) nav.className = 'navbar navbar-expand-md  navbar-dark bg-set fixed-top'; else nav.className = 'navbar navbar-expand-md  navbar-dark bg-set';
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




                  function write (obj, sentence, i, cb) {
                    if (i != sentence.length) {
                      setTimeout(function () {
                        i++
                        obj.innerHTML = sentence.substr(0, i+1) +' <em aria-hidden="true"></em>';
                        write(obj, sentence, i, cb)
                      }, 50)
                    } else {

                      cb()
                    }
                  }
                   function erase (obj, cb,i) {
                   var sentence = obj.innerText
                      if (sentence.length != 0) {
                       setTimeout(function () {
                       sentence = sentence.substr(0,sentence.length-1)

                       obj.innerText = sentence
                       erase(obj, cb)
                        }, 18/(i*(i/10000000)))
                        } else {
                        obj.innerText = " "
                        cb()
                     }
                    }
                    var typeline = document.querySelector("#typeline")

                     function writeerase(obj, sentence, time, cb) {
                      write(obj, sentence, 0, function () {
                       setTimeout(function () {
                       erase(obj, cb) }, time) })
                       }

                  var sentences = [
                    "an Engineer. ",
                    "a Developer. ",
                    "a Web Designer."
                  ]

                  var counter = 0
                  function loop () {
                    var sentence = sentences[counter % sentences.length]
                    writeerase(typeline, sentence, 1500, loop)
                    counter++
                  }

                  loop()
