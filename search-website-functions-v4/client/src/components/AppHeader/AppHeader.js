import React from 'react';
import AppHeaderAuth from '../AppHeaderAuth/AppHeaderAuth';

import logo from '../../images/wisely-logo.png';

import './AppHeader.css';

export default function AppHeader() {
  return (
    // <header className="header">
    //   <nav className="navbar navbar-expand-lg">
    //     <a className="navbar-brand" href="/">
    //       <img src={logo} height="50" className="navbar-logo" alt="Microsoft" />
    //     </a>
    //     <button className="navbar-toggler" type="button" data-toggle="collapse" data-target="#navbarSupportedContent" aria-controls="navbarSupportedContent" aria-expanded="false" aria-label="Toggle navigation">
    //       <span className="navbar-toggler-icon"></span>
    //     </button>

    //     <div className="collapse navbar-collapse" id="navbarSupportedContent">
    //       <ul className="navbar-nav mr-auto">
    //         <li className="nav-item">
    //           <a className="nav-link" href="/search">Buscar</a>
    //         </li>
    //       </ul>
    //     </div>

    //     <AppHeaderAuth />
    //   </nav>

    // </header>
    <div className="navbar bg-neutral">
      <div className="flex-1">
        <a className="btn btn-ghost normal-case text-xl" href='/'>
          <img src={logo} height="50" className="navbar-logo" alt="Microsoft" />
        </a>
        <ul className='menu flex-row'>
          <li><a className='text-base-100 text-base' href='/chatbot'>Chatbot</a></li>
          <li><a className='text-base-100 text-base' href='/search'>Buscar</a></li>
        </ul>

      </div>
      <AppHeaderAuth />
    </div>
  );
};
