let input
let slideIndex = 1;
let output
let parseDocument2 ;
let link;
var id;
var encrypted

$(document).ready(function () {

  /* Load output html in Monaco Editor*/
  sessionID = localStorage.getItem("storedSessionID");
  
  encrypted = window.location.href.split('#')[1];
  // console.log(encrypted);
  link = '/htmleditor/html-editor.html#'+encrypted;
  var decrypted = CryptoJS.AES.decrypt(encrypted, 'asdad123131asda');
  // console.log(decrypted);

  var decrypted_str = decrypted.toString(CryptoJS.enc.Utf8)
  // console.log(decrypted_str);

  id = decrypted_str.split('$')[0];
  // console.log(id);
 

  doc_path = decrypted_str.split('$')[1];
  // console.log(doc_path);

  // var html_output = doc_path.slice(0,doc_path.length-4)+'mod.html';
  
 
   var pdf_path = doc_path.split('out')[0];
  
   var html_mod_output = pdf_path + "out.mod.html"
   var html_output = pdf_path + "out.html"
  //  var http = new XMLHttpRequest();
  //  http.open('HEAD',"http://127.0.0.1:8000/"+ html_mod_output, false);
  //  http.send();
  //  if (http.status === 200) {
  //      console.log("File exists")
  //  } else {
  //      console.log("File doesn't exists")
  //  }

   var html_body;
   console.log(html_output)
   $.get("http://127.0.0.1:8000/"+ html_output, function (data) {
      html_body = data;
   })
   $.get("http://127.0.0.1:8000/"+ html_mod_output, function (data) {
      html_body = data;
   });
});

function parse(file){
    const parser = new DOMParser();
        let parseDocument = parser.parseFromString(file,"text/html");
        parseDocument2 = parser.parseFromString(file,"text/html");
        let elements = parseDocument.getElementsByTagName( 'img' );
        // console.log(parseDocument2)
        let length = elements.length
        if(length==0){
          home()}
        let y = length.toString()
        for (let i = 0; i < length; i++) {
            let j = i+1
            let x = j.toString();
            let numbertext = x + '/' + y
            let alt = elements[i].alt.toString();
            let src = elements[i].src.toString();
            
            let image = '<img class = "demo cursor" style="width:100%" onclick="currentSlide('+x+')"id = "image' + x + '" src = ' + src + ' alt =' + alt + '>';
            document.getElementById("images").innerHTML +='<div class="row">' + image + '</div>';


   
            let html_string = '<div class="mySlides" style="display: none;"><div class = "numbertext">'+ numbertext
            html_string += '</div><img style="width:100%; border: 5px solid #555;" src = ' + src 
            html_string += '><br><br><input type="text" id= "im'+ x +'" value = ' + alt +'>'
            html_string += '<br><br><button class = "button" onclick="plusSlides(-1)">previous</button>'
            html_string += '<button class = "button" onclick="plusSlides(1)">next</button>'
            html_string += '<br><br><button class = "button" tabindex="0" onClick = "final(parseDocument2)"  >Submit</button>'
            if(i==0){document.getElementById("slide").innerHTML = html_string}
            else {document.getElementById("slide").innerHTML += html_string}
        }
    showSlides(slideIndex);
}




function plusSlides(n) {
  showSlides(slideIndex += n);
}

function currentSlide(n) {
  showSlides(slideIndex = n);
}

function showSlides(n) {
  let i;
  let slides = document.getElementsByClassName("mySlides");
  let dots = document.getElementsByClassName("demo");
  if (n > slides.length) {slideIndex = 1}
  if (n < 1) {slideIndex = slides.length}
  for (i = 0; i < slides.length; i++) {
    slides[i].style.display = "none";
  }
  for (i = 0; i < dots.length; i++) {
    dots[i].className = dots[i].className.replace(" active", "");
  }
  slides[slideIndex-1].style.display = "block";
  dots[slideIndex-1].className += " active";

}


function final(text){
  const parser2 = new DOMParser();
  let parseDocument3 = parser2.parseFromString(document.getElementById("images").innerHTML,"text/html");

  let elements2 = parseDocument3.getElementsByTagName( 'img' );

  for(let j=0; j<elements2.length;j++){
    let a = elements2[j].id
    let b = (j+1).toString()
    if(document.getElementById("im"+b) != null){
      let val = document.getElementById("im"+b).value;
      // console.log(val)
      
      text.getElementsByTagName('img')[j].alt = val
    }

  }
  output = new XMLSerializer().serializeToString(text)
  // console.log(output)


    html_string = '<br><br><button class="create" onclick="xyz(output)" tabindex="0" >Download</button>'
    html_string += '<br><br><button class="save" onclick="save(output)" tabindex="0" >Save file</button>'
    html_string += '<br><br><button class="home" onclick="home()" tabindex="0" >Home</button>'
    document.getElementById("slide").innerHTML = html_string


}   

function home(){ 
  var x = '/htmleditor/html-editor.html#'+ encrypted;
  // console.log('location.href="/htmleditor/scrolling.html";')
  // console.log('location.href="'+x+'";')
  var link = document.createElement('a');
  link.setAttribute('onclick','location.href="'+x+'";')
  link.click();
  };

  function save(result) {
  var fd = new FormData();    
  fd.append( 'htmlData', output );
  fd.append( 'autoid', id );
  $.ajax({
      type: "POST",
      data: fd,
      url: "http://127.0.0.1:8000/updatemoddoc",
      processData: false,
      contentType: false,
      success: function (data) {
            alert("Successfully saved html!");
      },
      error: function (jqXHR, exception) {
          alert("Some error occured. Please try again after sometime!")
      }
  })
};

  function xyz(result) {
      
  // console.log(xyz)
    var textFile = null,
      makeTextFile = function (text) {
        var data = new Blob([text], {type: 'text/plain'});

        // If we are replacing a previously generated file we need to
        // manually revoke the object URL to avoid memory leaks.
        if (textFile !== null) {
          window.URL.revokeObjectURL(textFile);
        }
        console.log(window.URL.createObjectURL(data))
        textFile = window.URL.createObjectURL(data);

        return textFile;
      };
    console.log("download")
    var link = document.createElement('a');
    // var link = document.getElementById('downloadlink');
    link.href = makeTextFile(result);
    link.download = 'file.html'
    link.style.display = 'block';
    link.click();
    };
      
