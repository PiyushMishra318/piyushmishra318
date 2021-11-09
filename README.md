  <a href="https://wakatime.com/@1126c104-125d-4c52-840c-530d4fb4215e" title="Total time coded since May 31 2021"><img src="https://wakatime.com/badge/user/1126c104-125d-4c52-840c-530d4fb4215e.svg" align="center" alt="Total time coded since May 31 2021" /></a>

  <a href="https://github.com/piyushmishra318">
    <img style="width:45%" align="center" src="https://github-readme-stats.vercel.app/api/top-langs/?username=piyushmishra318&theme=cobalt&hide=css,html&show_icons=true&langs_count=100&layout=compact" />
  </a>
  <a href="https://github.com/piyushmishra318">
   <img style="width:45%" align="center" src="https://github-readme-stats.vercel.app/api?username=piyushmishra318&show_icons=true&theme=cobalt&include_all_commits=true&count_private=true"/>
  </a>
  
  <a href="https://github.com/anuraghazra/piyushmishra318" title="Total time coded since May 31 2021">
    <img style="width:45%" align="center" src="https://github-readme-stats.vercel.app/api/wakatime?username=piyushmishra&layout=compact"/>
</a>

  <a href="https://github.com/piyushmishra318">
   <img 
  align="center"
src="https://raw.githubusercontent.com/PiyushMishra318/piyushmishra318/master/LinkedIn%20Assessment%20Badges%20(1).png" style="width:45%"/>
  </a>

This is still a work in progress. I'll try to post demos for most of the following applications.

# Table of Contents

- [Tech stack](#techstack)
  - [Vue.js](#vue)
  - [Flutter](#flutter)
  - [Node](#node)
  - [Django](#django)
  - [IOT](#iot)
  - [Firebase](#firebase)
  - [AWS](#aws)
  - [React.js (Redux)](#react)
  - [C++](#cpp)
  - [Javascript](#js)

## Tech Stack <a name = "techstack"></a>

The following is the list of all the frameworks/tech I've worked on

### Vue.js <a name="vue"></a>

- [CoreUI](https://coreui.io/vue/demo/3.2.2/dark/#/dashboard) - Made two different Admin Panels made on CoreUi Admin Template.

- Api Integrations.

- [Socket.io](https://socket.io/) - Live updates.

- [Syncfusion Component Integrations](https://ej2.syncfusion.com/vue/demos/#/material/schedule/overview.html) - Used this package for a bunch of component integrations in the admin panels. Like Heirarchial grids, Schedulers, etc.

- Optimizations for fast delivery and browser caching.

### Flutter <a name="flutter"></a>

- Chat App - A chat app for a group chat with Firebase and socket.io with push notifications and qr code for joining chat groups.

- Made some contributions to [local_auth](https://github.com/PiyushMishra318/local_auth) package used for biometrics detection interface.

-[Tsukiyomi](https://github.com/PiyushMishra318/Tsukiyomi) <a name="tsukiyomi"></a> - - This is a GBA Games catelogue with an external GBA emulator with user management using firebase and the backend for user's statistics like paytime, favorites and downloads are being managed by Node.js + MongoDB backend. First Release is only launched for India.

- A webview application with qr code scanner with push notifications.

### Node <a name="node"></a>

- Microservice Architecture for authentication communications, etc.

- Authentication

  - [Passport](http://www.passportjs.org/) - All the different methods for authentications implemeted i.e Facebook, Twitter, Instagram, iCloud, Google, Github and Custom Use Cases.

  - Encryption stacks like bcrypt for user password encryptions and crypto for other purposes.

  - JSON Webtoken for authentication.

  - Cookie session management using express-session for single point authentication across the apex domain.

- [OpenCV.js](https://opencv.org) - OpenCV (Open Source Computer Vision Library) is an open source computer vision and machine learning software library. [Repo-link](https://github.com/PiyushMishra318/node-opencv)

- Serving a static website with a custom router with Node.js.

- Backend for an invoice and po service.

- A node script for extracting google page speed for a website.

- Backend for [Tsukiyomi](#tsukiyomi)

- A micro service that manages notifications through email, sms or whatsapp. Template management for notifications, queueing of requests based on priority and different event loops based on different use cases.

- An online wallet with referrals and affiliate integrations.

- [aws-sdk](https://aws.amazon.com/sdk-for-javascript/) - aws-sdk was used for creating/editing/managing distributions, lambdas, athena queries, aws ses, managing ssl certificates using amazon certificate manager.

### AWS

- Lambda

  - [Cloudfront Events](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/lambda-cloudfront-trigger-events.html) <a name="lambda1"></a> - These function are used to intercept and modify the request and responses for data served over cloudfront using [Lambda@Edge](https://aws.amazon.com/lambda/edge/).

  - On the fly image optimization - Compressing and converting the images into next gen format for eg. webp for chrome on the fly while serving the image through cloudfront. <strong>Demo under development</strong>.

  - [Amazon SES](https://aws.amazon.com/ses/) <a name="lambda2"></a> Email Templates - Edit/Delete/Create/SendEmail coupled with [AWS API-Gateway](https://aws.amazon.com/api-gateway/). <strong>Demo under development</strong>.

  - Serverless Node <a name="lambda3"></a> - Serverless Router made on Node.js for serving static conten coupled with [DynamoDB](https://aws.amazon.com/dynamodb/). <strong>Demo under development</strong>.

- [AWS API-Gateway](https://aws.amazon.com/api-gateway/) - Check [Lambda Section](#lambda2)

- [Amazon SES](https://aws.amazon.com/ses/) - Check [Lambda Section](#lambda2)

- [DynamoDB](https://aws.amazon.com/dynamodb/) - Check [Lambda Section](#lambda3)

- [Cloudfront](https://aws.amazon.com/cloudfront/) - Check [Lambda Section](#lambda1)

- [AWS Athena](https://aws.amazon.com/athena/) - Processing the logs from s3 into reports for analytics.

- [AWS ACM](https://aws.amazon.com/acm/) - Used for generating certficates for cloudfront/route53.

- [AWS EC2](https://aws.amazon.com/ec2/) - Used for deploying apps and services.

- [AWS Lightsail](https://aws.amazon.com/lightsail/) - Used for deploying apps and services

.... still updating other things I've worked with and what I'm allowed to show.
