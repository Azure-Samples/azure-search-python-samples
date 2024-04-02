import React, { useEffect, useState } from 'react';
import axios from 'axios';
import CircularProgress  from '@mui/material/CircularProgress';
import { useLocation, useNavigate } from "react-router-dom";

import Results from '../../components/Results/Results';
import Pager from '../../components/Pager/Pager';
import Facets from '../../components/Facets/Facets';
import SearchBar from '../../components/SearchBar/SearchBar';
import logo from '../../images/partselect.svg';
import "../../components/SearchBar/SearchBar.css"
import "./Search.css";
import { searchResponse } from '../../components/TestResponse';

export default function Search() {
  
  let location = useLocation();
  const navigate = useNavigate();
  
  const [ results, setResults ] = useState([]);
  const [ resultCount, setResultCount ] = useState(0);
  const [ currentPage, setCurrentPage ] = useState(1);
  const [ q, setQ ] = useState(new URLSearchParams(location.search).get('q') ?? "*");
  const [ top ] = useState(new URLSearchParams(location.search).get('top') ?? 8);
  const [ skip, setSkip ] = useState(new URLSearchParams(location.search).get('skip') ?? 0);
  const [ filters, setFilters ] = useState([]);
  const [ facets, setFacets ] = useState({});
  const [ isLoading, setIsLoading ] = useState(true);
  const [ preSelectedFilters, setPreSelectedFilters ] = useState([]);
  const [ preSelectedFlag, setPreSelectedFlag] = useState(false);
  let resultsPerPage = top;
  
  useEffect(() => {
      setIsLoading(true);
      setSkip((currentPage-1) * top);
      const body = {
        q: q,
        top: top,
        skip: skip,
        filters: filters,
        // fuzzy: true
      };
      if (filters === preSelectedFilters && preSelectedFlag===true) {
        setIsLoading(false);
      }
      else {
        axios.post('https://instaagentsearch-mwvqt7kpva-uc.a.run.app/search', body)
            .then(response => {
              // console.log(JSON.stringify(response.data))
              setResults(response.data.results);
              setFacets(response.data.facets);
              setResultCount(response.data.count);
              if (!preSelectedFlag) {
                setPreSelectedFilters(response.data.preselectedFilters);
              }
            })
            .catch(error => {
              console.log(error);
            });
            setIsLoading(false); 
      }
  }, [q, top, skip, filters, currentPage]);

  useEffect(() => {
    setFilters(preSelectedFilters);
    setPreSelectedFlag(true);
  }, [preSelectedFilters]);

  useEffect(() => {
    navigate('/search?q=' + q);  
    setCurrentPage(1);
    setFilters([]);
  }, [q]);


  let postSearchHandler = (searchTerm) => {
    setQ(searchTerm);
    setPreSelectedFlag(false);
  }

  var body;
  if (isLoading) {
    body = (
      <div className="col-md-9">
        <CircularProgress />
      </div>);
  } else {
    body = (
      <div className="col-md-9">
        <Results documents={results} top={top} skip={skip} count={resultCount} q={q}></Results>
        <Pager className="pager-style" currentPage={currentPage} resultCount={resultCount} resultsPerPage={resultsPerPage} setCurrentPage={setCurrentPage}></Pager>
      </div>
    )
  }

  return (
    <div>
    <header className="header">
      <nav className="navbar navbar-expand-lg">
        <a className="navbar-brand" href="/">
          <img src={logo} height="50" className="navbar-logo" alt="Microsoft" />
        </a>
      </nav>
    </header>
    <div className="search-bar-container-searchpage">
      <div className="search-bar-searchpage">
      <SearchBar onSearchHandler={postSearchHandler} page="searchpage"></SearchBar>
      </div>
    </div>
    <main className="main main--search container-fluid">
      <div className="row">
        <div className="col-md-3"> 
          <Facets facets={facets} filters={filters} preSelectedFilters={preSelectedFilters} setFilters={setFilters}></Facets>
        </div>
        {body}
      </div>
    </main>
    </div>
  );
}
