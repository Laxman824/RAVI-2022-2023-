/**
 * @fileoverview Javascript for html editor(which displays the output html after pdf analysis)
 *
 * @author Tuhinanksu Das
 */
 
var editor;
var editor1;
var decorations=[];
var sessionID = "";

$(document).ready(function () {

   /* Load output html in Monaco Editor*/
   sessionID = localStorage.getItem("storedSessionID");
   var encrypted = window.location.href.split('#')[1];
   var decrypted = CryptoJS.AES.decrypt(encrypted, 'asdad123131asda');
   var decrypted_str = decrypted.toString(CryptoJS.enc.Utf8)
   var id = decrypted_str.split('$')[0];
  

   var doc_path = decrypted_str.split('$')[1];
   console.log(doc_path);
   

   
 
   var pdf_path = doc_path.split('out')[0];
  
   var html_mod_output = pdf_path + "out.mod.html"
   var html_output = pdf_path + "out.html"

   document.getElementById('pdf_embed').src = "../" + pdf_path + "pdf";
   var html_body;
   console.log(html_output)
   $.get("http://127.0.0.1:8000/"+ html_output, function (data) {
      html_body = data;
   })
   $.get("http://127.0.0.1:8000/"+ html_mod_output, function (data) {
      html_body = data;
   });
   

   

   /* Load html in iframe*/
   var contents = $("iframe").contents(),
      body = contents.find("body"),
      styleTag = $("<style></style>").appendTo(contents.find("head"));
   require.config({ paths: { vs: '../node_modules/monaco-editor/min/vs' } });
   

   /* Monaco Editor instance for HTML
   Updates iframe realtime on change*/
   require(['vs/editor/editor.main'], function () {
      // console.log(html_body)
      editor = monaco.editor.create(document.getElementById('container'), {
         value: html_body,
         language: 'html',
         "autoIndent": true,
         "formatOnPaste": true,
         "formatOnType": true
      });
      setTimeout(() => {
         editor.getAction('editor.action.formatDocument').run();
      }, 1000);
      editor.onDidChangeModelContent(function () {
         body.html(editor.getValue());
      });
      editor.setScrollPosition({scrollTop: 0});
   });
   /* Monaco Editor instance for CSS*/
   require(['vs/editor/editor.main'], function () {
      editor1 = monaco.editor.create(document.getElementById('container1'), {
         language: 'css',
         "autoIndent": true,
         "formatOnPaste": true,
         "formatOnType": true
      });
      editor1.onDidChangeModelContent(function () {
         styleTag.text(editor1.getValue());
      });
   });
   /* Html tab click event*/
   $("#html_click").click(function () {
      document.getElementById("container").style.display = "block";
      document.getElementById("pdf_embed").style.display = "none";
   });
   /* Pdf tab click event*/
   $("#pdf_click").click(function () {
      document.getElementById("container").style.display = "none";
      document.getElementById("pdf_embed").style.display = "block";
   });
   /* Change focussed tab on click*/
   $(document).on("click", "nav a", function () {
      $('.nav a').removeClass('active');
      $(this).addClass("active");
   })
   /* Create pdf from html and download*/
   $("#submit").click(function () {
      // console.log(html_body)
      // var iframe_content = $("iframe").contents().find("html");
      // var doc = new jsPDF();
      // doc.fromHTML(iframe_content.html(), 15, 15, {
      //    'width': 170
      // });
      // doc.save('sample-file.pdf');
      var temp1 = $("iframe").contents().find("html").html();
      console.log(typeof(temp1))
      console.log(temp1)
      var fd = new FormData();    
      fd.append( 'htmlData', temp1 );
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
      });
   });
   /* Download the edited html*/
   $("#submit1").click(function () {
      var temp1 = $("iframe").contents().find("html");
      var link = document.createElement('a');
      var mimeType = 'text/html';

      link.setAttribute('download', 'sample-file.html');
      link.setAttribute('href', 'data:' + mimeType + ';charset=utf-8,' + encodeURIComponent(temp1.html()));
      link.click();
   });

   $("#submit3").click(function () {
      
      // var temp1 = $("iframe").contents().find("html");
      var link = document.createElement('a');
      // var mimeType = 'text/html';
      var x = '/htmleditor/image-editor.html#'+ encrypted;
      console.log('location.href="/htmleditor/image-editor.html";')
         console.log('location.href="'+x+'";')
      link.setAttribute('onclick','location.href="'+x+'";')
      link.click();
   });

   $("#ehome").click(function() {
      window.location.href = "/#"+sessionID;
   })
   // var abc = document.getElementById("iframe").contentWindow.document.body;
   // abc.click(function(event) {
   //    // var log = $('#log');
   //    alert("click");
   //    if(event.target.tagName == "p") {
   //       alert(event.target.tagName + ' was clicked.');
   //    }
   // });
   document.getElementById("iframe").contentWindow.document.body.onclick = function(event) {
      var formatted_html_string = editor.getValue();
      var target = event.target.id;
      var lines = formatted_html_string.split('\n');
      var i;
      for (i = 0; i < lines.length; ++i) {
         if(lines[i].indexOf(target) != -1){
            break;
        }
      };
      const decorationList = [
         {
            range: new monaco.Range(i+1, 1, i+1, 1),
            options: {
               isWholeLine: true,
               linesDecorationsClassName: 'myLineDecoration'
            }
         }
      ];
      
      editor.revealLineInCenter(i+1);
      editor.deltaDecorations(
         decorations,
         []
      );
      decorations=editor.deltaDecorations(
         [],
         decorationList
      );
   };
   console.log(html_body)

});


      
