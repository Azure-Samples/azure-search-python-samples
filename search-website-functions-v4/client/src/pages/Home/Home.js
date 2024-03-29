import React from "react";
import { useNavigate } from "react-router-dom";

import SearchBar from '../../components/SearchBar/SearchBar';
import "../../components/SearchBar/SearchBar.css";
import "./Home.css";
import "../../pages/Search/Search.css";
import logo from '../../images/cognitive_search.jpg';

export default function Home() {
  const navigate = useNavigate();
  const navigateToSearchPage = (q) => {
    if (!q || q === '') {
      q = '*'
    }
    navigate('/search?q=' + q);
  }

  return (
    <main className="main main--home">
      <div className="SearchApp">
      <header className="App-header">
      <div className="search-bar-container">
          <div className="search-bar">
        <SearchBar onSearchHandler={navigateToSearchPage}/>
        </div>
        </div>
      </header>
    </div>
    </main>
  );
};
