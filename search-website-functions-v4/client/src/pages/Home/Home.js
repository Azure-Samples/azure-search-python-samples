import React from "react";
import { useNavigate } from "react-router-dom";

import SearchBar from '../../components/SearchBar/SearchBar';

import "./Home.css";
import '../../App/App.css'
import "../../pages/Search/Search.css";
import logo from '../../images/coordinador-electrico-logo.png';


export default function Home() {
  const navigate = useNavigate();
  const navigateToSearchPage = (q) => {
    if (!q || q === '') {
      q = '*'
    }
    navigate('/search?q=' + q);
  }

  return (
    <main className="flex-grow">
      <div className="row home-search">
        <img className="logo" src={logo} alt="Cognitive Search"></img>
        <SearchBar postSearchHandler={navigateToSearchPage}></SearchBar>
      </div>
    </main>
  );
};
